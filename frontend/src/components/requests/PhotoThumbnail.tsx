import { ImageOff, Loader2, X } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { fetchPhotoObjectUrl } from "@/services/requests";

interface PhotoThumbnailProps {
  requestId: string;
  photoId: string;
  onDelete?: () => void;
  deleting?: boolean;
}

/**
 * Renders a request photo. The download endpoint needs a JWT, so we can't use a
 * bare <img src> — we fetch the bytes through the authenticated client into a
 * blob: URL and revoke it on unmount to avoid leaking memory.
 */
export function PhotoThumbnail({
  requestId,
  photoId,
  onDelete,
  deleting,
}: PhotoThumbnailProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;

    fetchPhotoObjectUrl(requestId, photoId)
      .then((u) => {
        objectUrl = u;
        if (active) setUrl(u);
        else URL.revokeObjectURL(u); // unmounted before resolve
      })
      .catch(() => {
        if (active) setFailed(true);
      });

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [requestId, photoId]);

  return (
    <div className="group relative aspect-square overflow-hidden rounded-lg border bg-muted">
      {failed ? (
        <div className="flex h-full items-center justify-center text-muted-foreground">
          <ImageOff className="size-5" />
        </div>
      ) : url ? (
        <img src={url} alt="Request photo" className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full items-center justify-center">
          <Loader2 className="size-5 animate-spin text-muted-foreground" />
        </div>
      )}

      {onDelete && (
        <Button
          variant="destructive"
          size="icon"
          className="absolute right-1 top-1 size-6 opacity-0 transition-opacity group-hover:opacity-100"
          onClick={onDelete}
          disabled={deleting}
          aria-label="Delete photo"
        >
          {deleting ? <Loader2 className="animate-spin" /> : <X />}
        </Button>
      )}
    </div>
  );
}
