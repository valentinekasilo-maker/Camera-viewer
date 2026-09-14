/**
 * Hook to get documentation URLs within ANDRO-Vision
 *
 * @returns {Object} An object containing:
 *   - getLocaleDocUrl: Function to get internal documentation URL for a given path
 *   - docDomain: "local"
 */
export function useDocDomain() {
  /**
   * Get documentation URL for a given path, routing internally to /docs
   * @param {string} path - Documentation path (e.g. "/configuration/live")
   * @returns {string} Internal /docs URL
   */
  const getLocaleDocUrl = (path: string): string => {
    const clean = path.toLowerCase().replace(/^\/+/, "");
    let section = "getting-started";

    if (clean.includes("live") || clean.includes("stream")) {
      section = "live-view";
    } else if (clean.includes("camera")) {
      section = "cameras";
    } else if (clean.includes("object") || clean.includes("detect") || clean.includes("model")) {
      section = "object-detection";
    } else if (clean.includes("audio")) {
      section = "audio-detection";
    } else if (clean.includes("record") || clean.includes("storage")) {
      section = "recording";
    } else if (clean.includes("zone")) {
      section = "zones";
    } else if (clean.includes("mask")) {
      section = "masks";
    } else if (clean.includes("notification") || clean.includes("mqtt")) {
      section = "notifications";
    } else if (clean.includes("genai") || clean.includes("semantic") || clean.includes("vision")) {
      section = "ai-vision";
    } else if (clean.includes("troubleshoot")) {
      section = "troubleshooting";
    } else if (clean.includes("performance") || clean.includes("hardware") || clean.includes("shm")) {
      section = "performance";
    }

    return `/docs?section=${section}`;
  };

  return {
    getLocaleDocUrl,
    docDomain: "local",
  };
}
