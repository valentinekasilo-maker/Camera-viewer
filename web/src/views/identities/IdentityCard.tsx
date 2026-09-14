import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CustomIdentity } from "@/types/identity";
import { formatDistanceToNow } from "date-fns";
import { useTranslation } from "react-i18next";
import {
  FaCar,
  FaCat,
  FaDog,
  FaEllipsisV,
  FaImage,
  FaMapMarkerAlt,
  FaMotorcycle,
  FaRegClock,
  FaTrashAlt,
  FaUser,
} from "react-icons/fa";
import { LuEye, LuPackage } from "react-icons/lu";

interface IdentityCardProps {
  identity: CustomIdentity;
  onViewDetails: (identity: CustomIdentity) => void;
  onDelete: (id: string) => void;
}

export function IdentityCard({
  identity,
  onViewDetails,
  onDelete,
}: IdentityCardProps) {
  const { t } = useTranslation(["views/identities", "common"]);

  const getStatusBadge = () => {
    switch (identity.status) {
      case "present":
        return (
          <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-400 border border-emerald-500/30">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            {identity.last_seen_location
              ? `${identity.last_seen_location}`
              : t("presence.currently_present")}
          </span>
        );
      case "not_recently_seen":
        return (
          <span className="flex items-center gap-1.5 rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-medium text-amber-400 border border-amber-500/30">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            {t("presence.not_recently_seen")}
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1.5 rounded-full bg-slate-500/15 px-2.5 py-0.5 text-xs font-medium text-slate-400 border border-slate-600/30">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
            {t("presence.away")}
          </span>
        );
    }
  };

  const getClassIcon = () => {
    const cls = (identity.object_class || "").toLowerCase();
    if (cls === "person") return <FaUser className="text-blue-400" />;
    if (["car", "truck", "bus"].includes(cls))
      return <FaCar className="text-amber-400" />;
    if (["motorcycle", "bicycle"].includes(cls))
      return <FaMotorcycle className="text-orange-400" />;
    if (cls === "dog") return <FaDog className="text-yellow-400" />;
    if (cls === "cat") return <FaCat className="text-pink-400" />;
    if (["backpack", "handbag", "suitcase", "package"].includes(cls))
      return <LuPackage className="text-emerald-400" />;
    return <FaCar className="text-cyan-400" />;
  };

  return (
    <Card className="group relative overflow-hidden rounded-xl border border-border/40 bg-card/60 backdrop-blur-md transition-all duration-300 hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5">
      <CardContent className="p-4 sm:p-5">
        <div className="flex items-start gap-4">
          {/* Avatar / Crop Thumbnail */}
          <div
            onClick={() => onViewDetails(identity)}
            className="relative h-20 w-20 flex-shrink-0 cursor-pointer overflow-hidden rounded-xl border border-border/50 bg-secondary/40 transition-transform group-hover:scale-105"
          >
            {identity.primary_reference_url ? (
              <img
                src={identity.primary_reference_url}
                alt={identity.name}
                className="h-full w-full object-cover"
                loading="lazy"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-3xl font-bold text-muted-foreground/40">
                {getClassIcon()}
              </div>
            )}
            <div className="absolute bottom-1 right-1 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm flex items-center gap-1">
              <FaImage className="text-[9px]" />
              {identity.reference_count}
            </div>
          </div>

          {/* Identity Information */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <h3
                onClick={() => onViewDetails(identity)}
                className="cursor-pointer truncate font-semibold text-base text-foreground transition-colors hover:text-primary"
              >
                {identity.name}
              </h3>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                  >
                    <FaEllipsisV className="h-3.5 w-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => onViewDetails(identity)}>
                    <LuEye className="mr-2 h-4 w-4" />
                    {t("identities_list.view_details")}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => onDelete(identity.id)}
                    className="text-destructive focus:text-destructive"
                  >
                    <FaTrashAlt className="mr-2 h-3.5 w-3.5" />
                    {t("identities_list.delete_identity")}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              <Badge
                variant="secondary"
                className="flex items-center gap-1 px-2 py-0.5 text-[11px] font-normal uppercase tracking-wider"
              >
                {getClassIcon()}
                <span>{identity.object_class}</span>
              </Badge>
              {identity.color && (
                <Badge
                  variant="outline"
                  className="px-2 py-0.5 text-[11px] font-normal text-muted-foreground border-border/60"
                >
                  {identity.color}
                </Badge>
              )}
              {identity.category && (
                <Badge
                  variant="outline"
                  className="px-2 py-0.5 text-[11px] font-normal text-muted-foreground border-border/60"
                >
                  {identity.category}
                </Badge>
              )}
            </div>

            {/* Presence & Location */}
            <div className="mt-3 flex items-center justify-between gap-2 border-t border-border/30 pt-2.5">
              <div>{getStatusBadge()}</div>
              {identity.last_seen_time && (
                <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                  <FaRegClock className="text-[10px]" />
                  {formatDistanceToNow(new Date(identity.last_seen_time), {
                    addSuffix: true,
                  })}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Footer info: Camera & Sightings count */}
        <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground/80 bg-secondary/20 rounded-lg px-2.5 py-1.5 border border-border/20">
          <div className="flex items-center gap-1.5 truncate">
            <FaMapMarkerAlt className="text-primary/70 text-[11px]" />
            <span className="truncate">
              {identity.last_seen_location || identity.last_seen_camera || "No location recorded"}
            </span>
          </div>
          <span className="font-mono text-[11px]">
            {identity.sightings_count || 0} sightings
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
