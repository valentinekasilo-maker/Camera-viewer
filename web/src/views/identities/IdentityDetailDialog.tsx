import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CustomIdentity } from "@/types/identity";
import axios from "axios";
import { format, formatDistanceToNow } from "date-fns";
import { useEffect, useState } from "react";
import {
  FaCamera,
  FaCloudUploadAlt,
  FaHistory,
  FaImages,
  FaInfoCircle,
  FaMapMarkerAlt,
  FaTrashAlt,
} from "react-icons/fa";
import { LuLoader } from "react-icons/lu";
import { toast } from "sonner";

interface IdentityDetailDialogProps {
  identityId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUpdated: () => void;
}

export function IdentityDetailDialog({
  identityId,
  open,
  onOpenChange,
  onUpdated,
}: IdentityDetailDialogProps) {
  const [identity, setIdentity] = useState<CustomIdentity | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const fetchDetail = async () => {
    if (!identityId) return;
    setIsLoading(true);
    try {
      const res = await axios.get(`identities/${identityId}`);
      if (res.data.success) {
        setIdentity(res.data.identity);
      }
    } catch (err) {
      toast.error("Failed to load identity details");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (open && identityId) {
      fetchDetail();
    } else {
      setIdentity(null);
    }
  }, [open, identityId]);

  const handleUploadAdditional = async (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    if (!e.target.files || !identityId) return;
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      files.forEach((file) => formData.append("photos", file));

      await axios.post(`identities/${identityId}/references`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      toast.success("Reference images added successfully");
      fetchDetail();
      onUpdated();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to upload references");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteReference = async (refId: string) => {
    try {
      await axios.delete(`identities/references/${refId}`);
      toast.success("Reference removed");
      fetchDetail();
      onUpdated();
    } catch (err) {
      toast.error("Failed to delete reference");
    }
  };

  if (!identity && isLoading) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-[700px] flex items-center justify-center p-12">
          <LuLoader className="h-8 w-8 animate-spin text-primary" />
        </DialogContent>
      </Dialog>
    );
  }

  if (!identity) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[750px] max-h-[90vh] overflow-y-auto">
        <DialogHeader className="border-b border-border/40 pb-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <DialogTitle className="text-2xl font-bold flex items-center gap-2.5">
                {identity.name}
              </DialogTitle>
              <DialogDescription className="mt-1 flex flex-wrap items-center gap-2">
                <Badge variant="secondary" className="uppercase text-xs font-mono">
                  {identity.object_class}
                </Badge>
                {identity.category && (
                  <Badge variant="outline" className="text-xs">
                    {identity.category}
                  </Badge>
                )}
                {identity.color && (
                  <Badge variant="outline" className="text-xs text-muted-foreground">
                    Color: {identity.color}
                  </Badge>
                )}
              </DialogDescription>
            </div>

            {/* Current Presence Status */}
            <div>
              {identity.status === "present" ? (
                <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/30">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  PRESENT
                </span>
              ) : identity.status === "not_recently_seen" ? (
                <span className="flex items-center gap-1.5 rounded-full bg-amber-500/15 px-3 py-1 text-xs font-medium text-amber-400 border border-amber-500/30">
                  <span className="h-2 w-2 rounded-full bg-amber-400" />
                  NOT RECENTLY SEEN
                </span>
              ) : (
                <span className="flex items-center gap-1.5 rounded-full bg-slate-500/15 px-3 py-1 text-xs font-medium text-slate-400 border border-slate-600/30">
                  AWAY
                </span>
              )}
            </div>
          </div>
        </DialogHeader>

        {/* Quick Highlights Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-secondary/20 p-3 rounded-xl border border-border/30 text-xs">
          <div>
            <span className="text-muted-foreground block">Last Location:</span>
            <span className="font-semibold text-foreground flex items-center gap-1 mt-0.5">
              <FaMapMarkerAlt className="text-primary text-[11px]" />
              {identity.last_seen_location || "Unknown"}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground block">Last Seen:</span>
            <span className="font-semibold text-foreground mt-0.5 block">
              {identity.last_seen_time
                ? formatDistanceToNow(new Date(identity.last_seen_time), {
                    addSuffix: true,
                  })
                : "Never"}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground block">First Registered:</span>
            <span className="font-semibold text-foreground mt-0.5 block">
              {identity.created_at
                ? format(new Date(identity.created_at), "MMM d, yyyy")
                : "N/A"}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground block">Total Sightings:</span>
            <span className="font-semibold text-foreground font-mono mt-0.5 block">
              {identity.sightings?.length || 0} events
            </span>
          </div>
        </div>

        {/* Tabs: Reference Photos vs Sighting Timeline */}
        <Tabs defaultValue="references" className="w-full pt-2">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="references" className="flex items-center gap-2">
              <FaImages className="text-xs" />
              Reference Photos ({identity.references?.length || 0})
            </TabsTrigger>
            <TabsTrigger value="sightings" className="flex items-center gap-2">
              <FaHistory className="text-xs" />
              Sightings Log ({identity.sightings?.length || 0})
            </TabsTrigger>
            <TabsTrigger value="overview" className="flex items-center gap-2">
              <FaInfoCircle className="text-xs" />
              Notes & Metadata
            </TabsTrigger>
          </TabsList>

          {/* Reference Photos Tab */}
          <TabsContent value="references" className="space-y-4 pt-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                Local reference features extracted from uploaded or confirmed crops:
              </p>
              <label className="cursor-pointer">
                <input
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={handleUploadAdditional}
                  disabled={isUploading}
                  className="hidden"
                />
                <Button size="sm" variant="outline" asChild disabled={isUploading}>
                  <span>
                    {isUploading ? (
                      <LuLoader className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <FaCloudUploadAlt className="mr-1.5 h-3.5 w-3.5 text-primary" />
                    )}
                    + Add Reference Photo
                  </span>
                </Button>
              </label>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {identity.references && identity.references.length > 0 ? (
                identity.references.map((ref) => (
                  <div
                    key={ref.id}
                    className="group relative h-28 rounded-xl overflow-hidden border border-border/50 bg-black/40"
                  >
                    <img
                      src={ref.url}
                      alt="Reference"
                      className="h-full w-full object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-between p-2">
                      <div className="flex justify-end">
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleDeleteReference(ref.id)}
                          className="h-6 w-6 p-0 rounded-full"
                        >
                          <FaTrashAlt className="h-3 w-3" />
                        </Button>
                      </div>
                      <Badge
                        variant="secondary"
                        className="self-start text-[10px] px-1.5 py-0 bg-black/70 text-white border-0"
                      >
                        {ref.source === "confirmed_event"
                          ? "Confirmed Event"
                          : "Upload"}
                      </Badge>
                    </div>
                  </div>
                ))
              ) : (
                <div className="col-span-4 text-center py-8 text-xs text-muted-foreground">
                  No reference photos uploaded. Click "+ Add Reference Photo" above.
                </div>
              )}
            </div>
          </TabsContent>

          {/* Sightings Timeline Tab */}
          <TabsContent value="sightings" className="pt-3">
            <div className="rounded-xl border border-border/40 overflow-hidden">
              <Table>
                <TableHeader className="bg-secondary/30">
                  <TableRow>
                    <TableHead className="w-16">Snapshot</TableHead>
                    <TableHead>Location Area</TableHead>
                    <TableHead>Camera</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead className="text-right">Timestamp</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {identity.sightings && identity.sightings.length > 0 ? (
                    identity.sightings.map((s) => (
                      <TableRow key={s.id}>
                        <TableCell className="p-2">
                          {s.snapshot_url ? (
                            <img
                              src={s.snapshot_url}
                              alt="Crop"
                              className="h-9 w-12 rounded object-cover border border-border/40"
                            />
                          ) : (
                            <div className="h-9 w-12 rounded bg-secondary/40 flex items-center justify-center text-muted-foreground">
                              <FaCamera className="text-xs" />
                            </div>
                          )}
                        </TableCell>
                        <TableCell className="font-medium text-xs">
                          <span className="flex items-center gap-1.5">
                            <FaMapMarkerAlt className="text-primary text-[10px]" />
                            {s.area}
                          </span>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground font-mono">
                          {s.camera}
                        </TableCell>
                        <TableCell className="text-xs">
                          <span className="rounded bg-primary/10 px-1.5 py-0.5 text-primary font-mono font-semibold text-[11px]">
                            {(s.confidence * 100).toFixed(0)}%
                          </span>
                        </TableCell>
                        <TableCell className="text-right text-xs text-muted-foreground">
                          {s.timestamp
                            ? format(new Date(s.timestamp), "MMM d, HH:mm:ss")
                            : "N/A"}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-6 text-xs text-muted-foreground">
                        No sightings recorded yet for this identity.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </TabsContent>

          {/* Overview & Notes Tab */}
          <TabsContent value="overview" className="space-y-4 pt-3 text-xs">
            <div className="space-y-2 rounded-xl border border-border/40 bg-secondary/10 p-4">
              <h4 className="font-semibold text-foreground">Description</h4>
              <p className="text-muted-foreground">
                {identity.description || "No description provided."}
              </p>
            </div>

            <div className="space-y-2 rounded-xl border border-border/40 bg-secondary/10 p-4">
              <h4 className="font-semibold text-foreground">Area & Access Notes</h4>
              <p className="text-muted-foreground">
                {identity.notes || "No notes recorded."}
              </p>
            </div>

            {identity.cameras_seen && identity.cameras_seen.length > 0 && (
              <div className="space-y-2 rounded-xl border border-border/40 bg-secondary/10 p-4">
                <h4 className="font-semibold text-foreground">Cameras Visited</h4>
                <div className="flex flex-wrap gap-2 pt-1">
                  {identity.cameras_seen.map((cam) => (
                    <Badge key={cam} variant="secondary" className="font-mono text-xs">
                      {cam}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
