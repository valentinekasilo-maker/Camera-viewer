import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ActiveTrack,
  CustomIdentity,
  ObjectSighting,
  UnknownTrack,
} from "@/types/identity";
import { AddIdentityDialog } from "@/views/identities/AddIdentityDialog";
import { CameraAreaSettings } from "@/views/identities/CameraAreaSettings";
import { IdentityCard } from "@/views/identities/IdentityCard";
import { IdentityDetailDialog } from "@/views/identities/IdentityDetailDialog";
import { UnknownReviewDialog } from "@/views/identities/UnknownReviewDialog";
import axios from "axios";
import { format, formatDistanceToNow } from "date-fns";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  FaCar,
  FaCheckCircle,
  FaCogs,
  FaFingerprint,
  FaHistory,
  FaMapMarkerAlt,
  FaPlus,
  FaQuestionCircle,
  FaRegClock,
  FaSearch,
  FaUserFriends,
  FaUsers,
} from "react-icons/fa";
import { LuRefreshCw } from "react-icons/lu";
import { toast } from "sonner";

export default function Identities() {
  const { t } = useTranslation(["views/identities", "common"]);

  const [activeTab, setActiveTab] = useState("presence");
  const [identities, setIdentities] = useState<CustomIdentity[]>([]);
  const [activeTracks, setActiveTracks] = useState<ActiveTrack[]>([]);
  const [unknownTracks, setUnknownTracks] = useState<UnknownTrack[]>([]);
  const [sightings, setSightings] = useState<ObjectSighting[]>([]);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");

  // Modals state
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [selectedIdentityId, setSelectedIdentityId] = useState<string | null>(
    null,
  );
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedUnknownTrack, setSelectedUnknownTrack] =
    useState<UnknownTrack | null>(null);
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);

  const fetchAllData = useCallback(async () => {
    try {
      const [idRes, tracksRes, unknownsRes, historyRes] = await Promise.all([
        axios.get("identities"),
        axios.get("identities/tracks/active"),
        axios.get("identities/tracks/unknown"),
        axios.get("identities/history?limit=100"),
      ]);

      if (idRes.data.success) setIdentities(idRes.data.identities);
      if (tracksRes.data.success) setActiveTracks(tracksRes.data.tracks);
      if (unknownsRes.data.success) setUnknownTracks(unknownsRes.data.unknowns);
      if (historyRes.data.success) setSightings(historyRes.data.history);
    } catch (err) {
      // quiet fallback
    }
  }, []);

  useEffect(() => {
    fetchAllData();
    // Auto-refresh presence every 5 seconds
    const interval = setInterval(fetchAllData, 5000);
    return () => clearInterval(interval);
  }, [fetchAllData]);

  const handleDeleteIdentity = async (id: string) => {
    try {
      await axios.delete(`identities/${id}`);
      toast.success("Identity deleted");
      fetchAllData();
    } catch (err) {
      toast.error("Failed to delete identity");
    }
  };

  const handleOpenDetail = (identity: CustomIdentity) => {
    setSelectedIdentityId(identity.id);
    setDetailDialogOpen(true);
  };

  const handleOpenReview = (track: UnknownTrack) => {
    setSelectedUnknownTrack(track);
    setReviewDialogOpen(true);
  };

  // Filtered identities list
  const filteredIdentities = identities.filter((id) => {
    const matchesSearch =
      searchQuery === "" ||
      id.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (id.color && id.color.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (id.category &&
        id.category.toLowerCase().includes(searchQuery.toLowerCase()));

    if (!matchesSearch) return false;

    if (categoryFilter === "vehicles") {
      return ["car", "motorcycle", "bicycle", "truck", "bus"].includes(
        id.object_class.toLowerCase(),
      );
    }
    if (categoryFilter === "people") {
      return id.is_person || id.object_class.toLowerCase() === "person";
    }
    if (categoryFilter === "pets") {
      return ["dog", "cat", "bird", "horse"].includes(
        id.object_class.toLowerCase(),
      );
    }
    if (categoryFilter === "items") {
      return ["backpack", "handbag", "suitcase", "package"].includes(
        id.object_class.toLowerCase(),
      );
    }
    return true;
  });

  const presentCount = identities.filter((i) => i.status === "present").length;

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background">
      {/* Header Banner */}
      <div className="border-b border-border/40 bg-card/40 px-6 py-4 backdrop-blur-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-foreground flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/15 text-primary">
                <FaFingerprint className="text-xl" />
              </span>
              {t("title")}
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              {t("subtitle")}
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchAllData}
              className="border-border/50 text-xs"
            >
              <LuRefreshCw className="mr-1.5 h-3.5 w-3.5" />
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={() => setAddDialogOpen(true)}
              className="bg-primary hover:bg-primary/90 text-xs font-semibold shadow-md shadow-primary/20"
            >
              <FaPlus className="mr-1.5 h-3 w-3" />
              {t("identities_list.enroll_btn")}
            </Button>
          </div>
        </div>
      </div>

      {/* Main Tabs Container */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="space-y-6"
        >
          {/* Tab Navigation */}
          <TabsList className="bg-secondary/40 border border-border/40 p-1 rounded-xl grid grid-cols-2 sm:grid-cols-5 gap-1 h-auto">
            <TabsTrigger
              value="presence"
              className="rounded-lg py-2 text-xs font-semibold data-[state=active]:bg-background data-[state=active]:shadow-sm flex items-center gap-1.5"
            >
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              {t("tabs.presence")}
              {presentCount > 0 && (
                <Badge
                  variant="secondary"
                  className="ml-1 px-1.5 py-0 text-[10px] bg-emerald-500/20 text-emerald-400"
                >
                  {presentCount}
                </Badge>
              )}
            </TabsTrigger>

            <TabsTrigger
              value="identities"
              className="rounded-lg py-2 text-xs font-semibold data-[state=active]:bg-background data-[state=active]:shadow-sm flex items-center gap-1.5"
            >
              <FaUsers className="text-xs text-primary" />
              {t("tabs.identities")} ({identities.length})
            </TabsTrigger>

            <TabsTrigger
              value="unknown"
              className="rounded-lg py-2 text-xs font-semibold data-[state=active]:bg-background data-[state=active]:shadow-sm flex items-center gap-1.5"
            >
              <FaQuestionCircle className="text-xs text-amber-400" />
              {t("tabs.unknown")}
              {unknownTracks.length > 0 && (
                <Badge
                  variant="secondary"
                  className="ml-1 px-1.5 py-0 text-[10px] bg-amber-500/20 text-amber-400"
                >
                  {unknownTracks.length}
                </Badge>
              )}
            </TabsTrigger>

            <TabsTrigger
              value="history"
              className="rounded-lg py-2 text-xs font-semibold data-[state=active]:bg-background data-[state=active]:shadow-sm flex items-center gap-1.5"
            >
              <FaHistory className="text-xs text-blue-400" />
              {t("tabs.history")}
            </TabsTrigger>

            <TabsTrigger
              value="settings"
              className="rounded-lg py-2 text-xs font-semibold data-[state=active]:bg-background data-[state=active]:shadow-sm flex items-center gap-1.5"
            >
              <FaCogs className="text-xs" />
              {t("tabs.settings")}
            </TabsTrigger>
          </TabsList>

          {/* TAB 1: LIVE PRESENCE & RADAR */}
          <TabsContent value="presence" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Enrolled Present Objects */}
              {identities
                .filter((i) => i.status === "present")
                .map((identity) => (
                  <Card
                    key={identity.id}
                    onClick={() => handleOpenDetail(identity)}
                    className="cursor-pointer border-emerald-500/40 bg-emerald-950/10 hover:border-emerald-500/80 transition-all rounded-xl shadow-sm hover:shadow-md"
                  >
                    <CardContent className="p-4 flex items-center gap-4">
                      <div className="relative h-16 w-16 rounded-xl overflow-hidden border border-emerald-500/40 bg-black/40 flex-shrink-0">
                        {identity.primary_reference_url ? (
                          <img
                            src={identity.primary_reference_url}
                            alt={identity.name}
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-emerald-400 font-bold">
                            {identity.is_person ? <FaUserFriends /> : <FaCar />}
                          </div>
                        )}
                        <span className="absolute top-1 left-1 h-2.5 w-2.5 rounded-full bg-emerald-400 animate-ping" />
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="font-bold text-sm truncate text-foreground">
                            {identity.name}
                          </h4>
                          <span className="rounded-full bg-emerald-500/20 px-2 py-0.2 text-[10px] font-semibold text-emerald-400">
                            PRESENT
                          </span>
                        </div>
                        <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                          <FaMapMarkerAlt className="text-emerald-400 text-[11px]" />
                          <span className="font-medium text-foreground">
                            {identity.last_seen_location || "Unknown Area"}
                          </span>
                        </div>
                        <p className="mt-1 text-[11px] text-muted-foreground/80 flex items-center gap-1">
                          <FaRegClock className="text-[10px]" />
                          {identity.last_seen_time
                            ? `${formatDistanceToNow(new Date(identity.last_seen_time))} ago`
                            : "Active now"}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))}

              {/* Active Unregistered Tracks */}
              {activeTracks
                .filter((t) => !t.is_known)
                .map((track) => (
                  <Card
                    key={track.track_id}
                    className="border-amber-500/40 bg-amber-950/10 rounded-xl"
                  >
                    <CardContent className="p-4 flex items-center gap-4">
                      <div className="h-16 w-16 rounded-xl overflow-hidden border border-amber-500/40 bg-black/40 flex-shrink-0 flex items-center justify-center">
                        {track.snapshot_url ? (
                          <img
                            src={track.snapshot_url}
                            alt={track.track_display_id}
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          <FaQuestionCircle className="text-amber-400 text-2xl" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="font-bold text-sm truncate text-foreground">
                            {track.track_display_id}
                          </h4>
                          <span className="rounded-full bg-amber-500/20 px-2 py-0.2 text-[10px] font-semibold text-amber-400">
                            UNKNOWN {track.object_class.toUpperCase()}
                          </span>
                        </div>
                        <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                          <FaMapMarkerAlt className="text-amber-400 text-[11px]" />
                          <span>{track.area}</span>
                        </div>
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          Seen {track.seconds_ago}s ago via {track.camera}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
            </div>

            {identities.filter((i) => i.status === "present").length === 0 &&
              activeTracks.filter((t) => !t.is_known).length === 0 && (
                <div className="text-center py-16 border border-dashed border-border/50 rounded-2xl bg-secondary/10">
                  <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-secondary/50 text-muted-foreground mb-3">
                    <FaFingerprint className="text-2xl" />
                  </span>
                  <h3 className="text-base font-bold text-foreground">
                    {t("presence.no_active_tracks")}
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
                    Monitored areas are clear. Sighted objects will dynamically appear here in real-time.
                  </p>
                </div>
              )}
          </TabsContent>

          {/* TAB 2: REGISTERED IDENTITIES LIST */}
          <TabsContent value="identities" className="space-y-4">
            {/* Search & Category Filter Bar */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-secondary/20 p-3 rounded-xl border border-border/30">
              <div className="relative flex-1">
                <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-xs" />
                <Input
                  placeholder={t("identities_list.search_placeholder")}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 bg-background/80 h-9 text-xs"
                />
              </div>

              <div className="flex flex-wrap items-center gap-1.5">
                {[
                  { id: "all", label: `All (${identities.length})` },
                  { id: "vehicles", label: "Vehicles" },
                  { id: "people", label: "People" },
                  { id: "pets", label: "Pets" },
                  { id: "items", label: "Items" },
                ].map((btn) => (
                  <Button
                    key={btn.id}
                    variant={categoryFilter === btn.id ? "default" : "outline"}
                    size="sm"
                    onClick={() => setCategoryFilter(btn.id)}
                    className="h-8 text-xs rounded-lg px-3"
                  >
                    {btn.label}
                  </Button>
                ))}
              </div>
            </div>

            {/* Grid of Identities */}
            {filteredIdentities.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredIdentities.map((identity) => (
                  <IdentityCard
                    key={identity.id}
                    identity={identity}
                    onViewDetails={handleOpenDetail}
                    onDelete={handleDeleteIdentity}
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-16 border border-dashed border-border/50 rounded-2xl bg-secondary/10">
                <p className="text-sm font-semibold text-foreground">
                  {t("identities_list.no_identities")}
                </p>
              </div>
            )}
          </TabsContent>

          {/* TAB 3: UNKNOWN REVIEW QUEUE */}
          <TabsContent value="unknown" className="space-y-4">
            <div className="bg-secondary/20 p-4 rounded-xl border border-border/30 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-sm text-foreground">
                  {t("unknown_queue.title")}
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {t("unknown_queue.subtitle")}
                </p>
              </div>
              <Badge variant="outline" className="font-mono text-xs">
                {unknownTracks.length} pending
              </Badge>
            </div>

            {unknownTracks.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {unknownTracks.map((track) => (
                  <Card
                    key={track.track_id}
                    className="border border-amber-500/30 bg-card/60 rounded-xl overflow-hidden"
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start gap-4">
                        <div className="h-20 w-20 rounded-xl overflow-hidden border border-border/50 bg-black/40 flex-shrink-0">
                          {track.snapshot_url ? (
                            <img
                              src={track.snapshot_url}
                              alt={track.track_display_id}
                              className="h-full w-full object-cover"
                            />
                          ) : (
                            <div className="flex h-full w-full items-center justify-center text-amber-400 font-bold text-xl">
                              ?
                            </div>
                          )}
                        </div>

                        <div className="flex-1 min-w-0 text-xs space-y-1">
                          <h4 className="font-bold text-sm text-foreground">
                            {track.track_display_id}
                          </h4>
                          <Badge variant="secondary" className="uppercase text-[10px]">
                            {track.object_class}
                          </Badge>
                          <p className="text-muted-foreground flex items-center gap-1">
                            <FaMapMarkerAlt className="text-primary text-[10px]" />
                            {track.area} ({track.camera})
                          </p>
                          <p className="text-[11px] text-muted-foreground">
                            {track.sighting_count} sightings across cameras
                          </p>
                        </div>
                      </div>

                      <div className="mt-3 border-t border-border/30 pt-3 flex items-center gap-2">
                        <Button
                          size="sm"
                          onClick={() => handleOpenReview(track)}
                          className="flex-1 text-xs font-semibold"
                        >
                          <FaCheckCircle className="mr-1.5 h-3.5 w-3.5" />
                          {t("unknown_queue.identify_btn")}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-16 border border-dashed border-border/50 rounded-2xl bg-secondary/10">
                <FaCheckCircle className="mx-auto text-3xl text-emerald-400 mb-2" />
                <h3 className="text-sm font-bold text-foreground">
                  {t("unknown_queue.no_unknowns")}
                </h3>
              </div>
            )}
          </TabsContent>

          {/* TAB 4: SIGHTINGS & MOVEMENT HISTORY */}
          <TabsContent value="history" className="space-y-4">
            <div className="bg-secondary/20 p-4 rounded-xl border border-border/30">
              <h3 className="font-bold text-sm text-foreground">
                {t("history.title")}
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t("history.subtitle")}
              </p>
            </div>

            <div className="rounded-xl border border-border/40 bg-card/60 overflow-hidden">
              <Table>
                <TableHeader className="bg-secondary/40">
                  <TableRow>
                    <TableHead className="w-16">Snapshot</TableHead>
                    <TableHead>Identity / Track</TableHead>
                    <TableHead>Monitored Area</TableHead>
                    <TableHead>Camera Stream</TableHead>
                    <TableHead>Match Confidence</TableHead>
                    <TableHead className="text-right">Timestamp</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sightings.length > 0 ? (
                    sightings.map((s) => (
                      <TableRow key={s.id} className="hover:bg-secondary/20">
                        <TableCell className="p-2.5">
                          {s.snapshot_url ? (
                            <img
                              src={s.snapshot_url}
                              alt="Sighting"
                              className="h-10 w-14 rounded-lg object-cover border border-border/40"
                            />
                          ) : (
                            <div className="h-10 w-14 rounded-lg bg-secondary/40 flex items-center justify-center text-muted-foreground text-xs">
                              <FaHistory />
                            </div>
                          )}
                        </TableCell>
                        <TableCell className="font-semibold text-xs text-foreground">
                          {s.identity_name || s.track_id}
                        </TableCell>
                        <TableCell className="text-xs font-medium">
                          <span className="flex items-center gap-1.5">
                            <FaMapMarkerAlt className="text-primary text-[11px]" />
                            {s.area}
                          </span>
                        </TableCell>
                        <TableCell className="text-xs font-mono text-muted-foreground">
                          {s.camera}
                        </TableCell>
                        <TableCell className="text-xs">
                          <span className="rounded bg-primary/10 px-2 py-0.5 text-primary font-mono font-bold text-[11px]">
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
                      <TableCell colSpan={6} className="text-center py-12 text-xs text-muted-foreground">
                        {t("history.no_history")}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </TabsContent>

          {/* TAB 5: CAMERA AREAS & SETTINGS */}
          <TabsContent value="settings" className="space-y-4">
            <CameraAreaSettings />
          </TabsContent>
        </Tabs>
      </div>

      {/* Dialogs */}
      <AddIdentityDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        onSuccess={fetchAllData}
      />

      <IdentityDetailDialog
        identityId={selectedIdentityId}
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
        onUpdated={fetchAllData}
      />

      <UnknownReviewDialog
        track={selectedUnknownTrack}
        open={reviewDialogOpen}
        onOpenChange={setReviewDialogOpen}
        enrolledIdentities={identities}
        onSuccess={fetchAllData}
      />
    </div>
  );
}
