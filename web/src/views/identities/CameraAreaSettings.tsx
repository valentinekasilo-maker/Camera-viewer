import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { CameraAreaMapping, IdentitySettingsConfig } from "@/types/identity";
import axios from "axios";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { FaCamera, FaCheck, FaCogs, FaMapMarkedAlt } from "react-icons/fa";
import { LuLoader } from "react-icons/lu";
import { toast } from "sonner";

export function CameraAreaSettings() {
  const { t } = useTranslation(["views/identities", "common"]);

  const [mappings, setMappings] = useState<CameraAreaMapping[]>([]);
  const [config, setConfig] = useState<IdentitySettingsConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [areasRes, configRes] = await Promise.all([
        axios.get("identities/camera-areas"),
        axios.get("identities/config"),
      ]);
      if (areasRes.data.success) setMappings(areasRes.data.camera_areas);
      if (configRes.data.success) setConfig(configRes.data.config);
    } catch (err) {
      toast.error("Failed to load camera areas and settings");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAreaChange = (camera: string, newArea: string) => {
    setMappings((prev) =>
      prev.map((m) => (m.camera === camera ? { ...m, area: newArea } : m)),
    );
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await Promise.all([
        axios.put("identities/camera-areas", mappings),
        config ? axios.put("identities/config", config) : Promise.resolve(),
      ]);
      toast.success(t("settings.saved_toast"));
    } catch (err: any) {
      toast.error("Failed to save settings");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <LuLoader className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Camera to Area Mapping */}
      <Card className="border border-border/40 bg-card/60 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <FaMapMarkedAlt className="text-primary" />
            {t("settings.camera_areas")}
          </CardTitle>
          <CardDescription>
            Map each camera stream to a human-readable monitored location area (e.g. Gate, Living Room, Driveway, Veranda).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {mappings.map((m) => (
              <div
                key={m.camera}
                className="flex items-center gap-3 p-3 rounded-xl border border-border/40 bg-secondary/20"
              >
                <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center text-primary flex-shrink-0">
                  <FaCamera className="text-sm" />
                </div>
                <div className="flex-1 min-w-0">
                  <span className="text-[11px] font-mono text-muted-foreground block truncate">
                    {m.camera}
                  </span>
                  <Input
                    value={m.area}
                    onChange={(e) => handleAreaChange(m.camera, e.target.value)}
                    placeholder="e.g. Gate, Driveway, Veranda"
                    className="h-8 mt-1 text-xs bg-background/80"
                  />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Matching & Recognition Thresholds */}
      {config && (
        <Card className="border border-border/40 bg-card/60 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <FaCogs className="text-primary" />
              Identity Recognition & Tracking Parameters
            </CardTitle>
            <CardDescription>
              Fine-tune local similarity thresholds, track retention, and presence status timeouts.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Object Threshold Slider */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <Label className="font-semibold">
                  {t("settings.matching_threshold_object")}
                </Label>
                <span className="font-mono text-primary font-bold">
                  {(config.matching_threshold_object * 100).toFixed(0)}%
                </span>
              </div>
              <Slider
                value={[config.matching_threshold_object * 100]}
                min={50}
                max={95}
                step={1}
                onValueChange={([val]) =>
                  setConfig({ ...config, matching_threshold_object: val / 100 })
                }
              />
              <p className="text-[11px] text-muted-foreground">
                Minimum cosine appearance similarity required to match a detected vehicle or object to an enrolled identity (Default: 70%).
              </p>
            </div>

            {/* Person Threshold Slider */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <Label className="font-semibold">
                  {t("settings.matching_threshold_person")}
                </Label>
                <span className="font-mono text-primary font-bold">
                  {(config.matching_threshold_person * 100).toFixed(0)}%
                </span>
              </div>
              <Slider
                value={[config.matching_threshold_person * 100]}
                min={60}
                max={98}
                step={1}
                onValueChange={([val]) =>
                  setConfig({ ...config, matching_threshold_person: val / 100 })
                }
              />
              <p className="text-[11px] text-muted-foreground">
                Privacy-first strict threshold for recognized people. Unenrolled people strictly remain Unknown Person (Default: 75%).
              </p>
            </div>

            {/* Presence Timeout Slider */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <Label className="font-semibold">
                  {t("settings.presence_timeout")}
                </Label>
                <span className="font-mono text-primary font-bold">
                  {config.presence_timeout_seconds}s (
                  {(config.presence_timeout_seconds / 60).toFixed(1)} min)
                </span>
              </div>
              <Slider
                value={[config.presence_timeout_seconds]}
                min={30}
                max={600}
                step={15}
                onValueChange={([val]) =>
                  setConfig({ ...config, presence_timeout_seconds: val })
                }
              />
            </div>

            {/* Cross-camera switch */}
            <div className="flex items-center justify-between p-3 rounded-xl border border-border/30 bg-secondary/10">
              <div className="space-y-0.5">
                <Label className="text-xs font-semibold cursor-pointer">
                  {t("settings.cross_camera")}
                </Label>
                <p className="text-[11px] text-muted-foreground">
                  Correlate continuous object tracks across nearby cameras within spatial-temporal time windows.
                </p>
              </div>
              <Switch
                checked={config.enable_cross_camera_tracking}
                onCheckedChange={(checked) =>
                  setConfig({ ...config, enable_cross_camera_tracking: checked })
                }
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={isSaving} className="px-6">
          {isSaving ? (
            <LuLoader className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <FaCheck className="mr-2 h-4 w-4" />
          )}
          {t("settings.save_btn")}
        </Button>
      </div>
    </div>
  );
}
