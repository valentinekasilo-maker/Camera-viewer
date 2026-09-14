import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  RadioGroup,
  RadioGroupItem,
} from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CustomIdentity, UnknownTrack } from "@/types/identity";
import axios from "axios";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  FaCheckCircle,
  FaLink,
  FaPlusCircle,
  FaQuestionCircle,
  FaTrashAlt,
} from "react-icons/fa";
import { LuLoader } from "react-icons/lu";
import { toast } from "sonner";

interface UnknownReviewDialogProps {
  track: UnknownTrack | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  enrolledIdentities: CustomIdentity[];
  onSuccess: () => void;
}

export function UnknownReviewDialog({
  track,
  open,
  onOpenChange,
  enrolledIdentities,
  onSuccess,
}: UnknownReviewDialogProps) {
  const { t } = useTranslation(["views/identities", "common"]);

  const [action, setAction] = useState<"create_new" | "link_existing">("create_new");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("Personal Vehicle");
  const [color, setColor] = useState("");
  const [notes, setNotes] = useState("");
  const [selectedIdentityId, setSelectedIdentityId] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!track) return null;

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      if (action === "create_new") {
        if (!name.trim()) {
          toast.error("Name is required");
          setIsSubmitting(false);
          return;
        }

        await axios.post(`identities/tracks/${track.track_id}/identify`, {
          action: "create_new",
          name: name.trim(),
          category,
          color: color.trim() || undefined,
          notes: notes.trim() || undefined,
        });

        toast.success(`Track enrolled as "${name}" with confirmed learning`);
      } else {
        if (!selectedIdentityId) {
          toast.error("Please select an existing identity to link");
          setIsSubmitting(false);
          return;
        }

        await axios.post(`identities/tracks/${track.track_id}/identify`, {
          action: "link_existing",
          identity_id: selectedIdentityId,
        });

        toast.success("Track linked with confirmed match learning");
      }

      onOpenChange(false);
      onSuccess();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to process track");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDismiss = async () => {
    setIsSubmitting(true);
    try {
      await axios.delete(`identities/tracks/${track.track_id}`);
      toast.success("Track dismissed from queue");
      onOpenChange(false);
      onSuccess();
    } catch (err) {
      toast.error("Failed to dismiss track");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Filter existing identities matching the track object_class
  const matchingClassIdentities = enrolledIdentities.filter(
    (id) => id.object_class.toLowerCase() === track.object_class.toLowerCase(),
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold flex items-center gap-2">
            <FaQuestionCircle className="text-amber-400" />
            Review {track.track_display_id}
          </DialogTitle>
          <DialogDescription>
            Confirm identity for this unclassified {track.object_class} sighted at {track.area}.
          </DialogDescription>
        </DialogHeader>

        {/* Snapshot and Track details */}
        <div className="flex items-center gap-4 bg-secondary/20 p-3 rounded-xl border border-border/30">
          <div className="h-24 w-24 rounded-lg overflow-hidden border border-border/50 bg-black/40 flex-shrink-0">
            {track.snapshot_url ? (
              <img
                src={track.snapshot_url}
                alt={track.track_display_id}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
                No Snapshot
              </div>
            )}
          </div>
          <div className="text-xs space-y-1">
            <p>
              <span className="text-muted-foreground">Camera:</span>{" "}
              <span className="font-mono font-semibold text-foreground">
                {track.camera}
              </span>
            </p>
            <p>
              <span className="text-muted-foreground">Location Area:</span>{" "}
              <span className="font-semibold text-foreground">{track.area}</span>
            </p>
            <p>
              <span className="text-muted-foreground">Sightings:</span>{" "}
              <span className="font-semibold text-foreground">
                {track.sighting_count} appearances
              </span>
            </p>
          </div>
        </div>

        <form onSubmit={handleConfirm} className="space-y-4 pt-2">
          {/* Action Choice: Create New vs Link Existing */}
          <div className="space-y-2">
            <Label className="text-xs font-semibold">Choose Action</Label>
            <RadioGroup
              value={action}
              onValueChange={(val: any) => setAction(val)}
              className="grid grid-cols-2 gap-3"
            >
              <div
                className={`flex items-center gap-2 rounded-xl border p-3 cursor-pointer transition-colors ${
                  action === "create_new"
                    ? "border-primary bg-primary/10"
                    : "border-border/40 bg-secondary/10"
                }`}
                onClick={() => setAction("create_new")}
              >
                <RadioGroupItem value="create_new" id="create_new" />
                <Label htmlFor="create_new" className="cursor-pointer text-xs font-medium flex items-center gap-1.5">
                  <FaPlusCircle className="text-primary" />
                  Create New Identity
                </Label>
              </div>

              <div
                className={`flex items-center gap-2 rounded-xl border p-3 cursor-pointer transition-colors ${
                  action === "link_existing"
                    ? "border-primary bg-primary/10"
                    : "border-border/40 bg-secondary/10"
                }`}
                onClick={() => setAction("link_existing")}
              >
                <RadioGroupItem value="link_existing" id="link_existing" />
                <Label htmlFor="link_existing" className="cursor-pointer text-xs font-medium flex items-center gap-1.5">
                  <FaLink className="text-primary" />
                  Link to Existing
                </Label>
              </div>
            </RadioGroup>
          </div>

          {action === "create_new" ? (
            <div className="space-y-3 border-t border-border/30 pt-3">
              <div className="space-y-1.5">
                <Label htmlFor="new-name" className="text-xs font-semibold">
                  Identity Name *
                </Label>
                <Input
                  id="new-name"
                  placeholder="e.g. Delivery Van, White Toyota Harrier, Neighbor John"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required={action === "create_new"}
                  className="bg-secondary/40"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Category</Label>
                  <Input
                    placeholder="e.g. Vehicle, Visitor, Family"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="bg-secondary/40"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Color</Label>
                  <Input
                    placeholder="e.g. White, Silver, Blue"
                    value={color}
                    onChange={(e) => setColor(e.target.value)}
                    className="bg-secondary/40"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Notes / Monitored Locations</Label>
                <Input
                  placeholder="e.g. Daily delivery van. Seen frequently around Gate."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="bg-secondary/40 text-xs"
                />
              </div>
            </div>
          ) : (
            <div className="space-y-2 border-t border-border/30 pt-3">
              <Label className="text-xs font-semibold">
                Select Existing {track.object_class.toUpperCase()} Identity
              </Label>
              {matchingClassIdentities.length > 0 ? (
                <Select
                  value={selectedIdentityId}
                  onValueChange={setSelectedIdentityId}
                >
                  <SelectTrigger className="bg-secondary/40">
                    <SelectValue placeholder="Choose identity to link..." />
                  </SelectTrigger>
                  <SelectContent>
                    {matchingClassIdentities.map((id) => (
                      <SelectItem key={id.id} value={id.id}>
                        {id.name} ({id.category})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <p className="text-xs text-muted-foreground py-2">
                  No existing {track.object_class} identities enrolled. Please choose "Create New Identity".
                </p>
              )}
            </div>
          )}

          <DialogFooter className="flex items-center justify-between gap-2 pt-2 border-t border-border/30">
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={handleDismiss}
              disabled={isSubmitting}
            >
              <FaTrashAlt className="mr-1.5 h-3 w-3" />
              {t("unknown_queue.dismiss_btn")}
            </Button>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onOpenChange(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={isSubmitting}>
                {isSubmitting ? (
                  <LuLoader className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <FaCheckCircle className="mr-1.5 h-3.5 w-3.5" />
                )}
                Confirm & Learn
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
