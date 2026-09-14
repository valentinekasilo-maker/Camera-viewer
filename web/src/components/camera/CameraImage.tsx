import { useApiHost } from "@/api";
import { useEffect, useMemo, useRef, useState } from "react";
import useSWR from "swr";
import ActivityIndicator from "../indicators/activity-indicator";
import { useResizeObserver } from "@/hooks/resize-observer";
import { isDesktop } from "react-device-detect";
import { cn } from "@/lib/utils";
import { useEnabledState } from "@/api/ws";

type CameraImageProps = {
  className?: string;
  camera: string;
  onload?: () => void;
  searchParams?: string;
};

export default function CameraImage({
  className,
  camera,
  onload,
  searchParams = "",
}: CameraImageProps) {
  const { data: config } = useSWR("config");
  const apiHost = useApiHost();
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [currentValidSrc, setCurrentValidSrc] = useState<string | null>(null);
  const [fetchError, setFetchError] = useState<boolean>(false);
  const [isPortraitImage, setIsPortraitImage] = useState<boolean>(false);

  const cameraConfig = config?.cameras?.[camera];
  const { name } = cameraConfig ?? { name: camera };
  const { payload: enabledState } = useEnabledState(camera);
  const enabled = enabledState ? enabledState === "ON" : true;

  const [{ width: containerWidth, height: containerHeight }] =
    useResizeObserver(containerRef);

  const requestHeight = useMemo(() => {
    if (!cameraConfig || containerHeight === 0) {
      return 360;
    }

    return Math.min(
      cameraConfig.detect.height,
      Math.round(containerHeight * (isDesktop ? 1.1 : 1.25)),
    );
  }, [cameraConfig, containerHeight]);

  // Target URL to fetch
  const targetSrc = useMemo(() => {
    if (!config || !enabled) return null;
    return `${apiHost}api/${name}/latest.webp?height=${requestHeight}${
      searchParams ? `&${searchParams}` : ""
    }`;
  }, [apiHost, name, searchParams, requestHeight, config, enabled]);

  // Seamless dual-buffer snapshot loader
  useEffect(() => {
    if (!targetSrc) return;

    let isMounted = true;

    const imgLoader = new Image();
    imgLoader.src = targetSrc;

    imgLoader.onload = () => {
      if (!isMounted) return;
      if (containerWidth && containerHeight) {
        const { naturalWidth, naturalHeight } = imgLoader;
        setIsPortraitImage(
          naturalWidth / naturalHeight < containerWidth / containerHeight,
        );
      }
      setCurrentValidSrc(targetSrc);
      setFetchError(false);
      onload?.();
    };

    imgLoader.onerror = () => {
      if (!isMounted) return;
      // Keep previous valid image, mark subtle error
      setFetchError(true);
    };

    return () => {
      isMounted = false;
    };
  }, [targetSrc, containerWidth, containerHeight, onload]);

  return (
    <div className={cn("relative overflow-hidden", className)} ref={containerRef}>
      {enabled ? (
        currentValidSrc ? (
          <>
            <img
              src={currentValidSrc}
              alt={name}
              className={cn(
                "object-cover transition-opacity duration-300",
                isPortraitImage ? "h-full w-auto" : "h-auto w-full",
                "rounded-lg md:rounded-2xl",
              )}
              loading="lazy"
            />
            {fetchError && (
              <div
                className="absolute right-2 top-2 z-10 size-2 rounded-full bg-amber-500/80 shadow-[0_0_6px_rgba(245,158,11,0.8)]"
                title="Snapshot refresh temporarily delayed (holding last valid frame)"
              />
            )}
          </>
        ) : (
          <div className="flex size-full items-center justify-center rounded-lg bg-neutral-900 md:rounded-2xl">
            <ActivityIndicator />
          </div>
        )
      ) : (
        <div className="size-full rounded-lg border-2 border-muted bg-background_alt text-center md:rounded-2xl" />
      )}
    </div>
  );
}
