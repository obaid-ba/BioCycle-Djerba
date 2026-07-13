import "leaflet/dist/leaflet.css";

import L from "leaflet";
import { Building2 } from "lucide-react";
import { useMemo } from "react";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";

import { PageToolbar } from "@/components/common/PageToolbar";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { useHotels } from "@/hooks/useHotels";
import { hotelStatusVariant, humanize } from "@/lib/statusBadge";

// Djerba island centre — sensible default view.
const DJERBA_CENTER: [number, number] = [33.807, 10.845];

/**
 * CSS-based marker so we don't depend on Leaflet's default PNG icons (whose
 * bundler-broken image paths are a well-known footgun).
 */
function dotIcon(color: string): L.DivIcon {
  return L.divIcon({
    className: "",
    html: `<span style="display:block;width:16px;height:16px;border-radius:9999px;background:${color};border:2px solid white;box-shadow:0 0 0 1px rgba(0,0,0,.25)"></span>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

const hotelIcon = dotIcon("hsl(142 71% 40%)");

export function MapView() {
  const hotelsQuery = useHotels({ page_size: 100 });

  const hotels = useMemo(
    () => (hotelsQuery.data?.items ?? []).filter((h) => h.latitude != null && h.longitude != null),
    [hotelsQuery.data],
  );

  const placed = hotels.length;

  return (
    <div className="space-y-6">
      <PageToolbar
        title="Map"
        description="Geographic view of hotels across Djerba."
      >
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="size-3 rounded-full" style={{ background: "hsl(142 71% 40%)" }} />
            Hotels ({hotels.length})
          </span>
        </div>
      </PageToolbar>

      <Card className="overflow-hidden">
        {placed === 0 ? (
          <div className="flex h-[60vh] flex-col items-center justify-center gap-2 text-center">
            <Building2 className="size-6 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No hotels have coordinates yet. Add latitude/longitude to see them
              here.
            </p>
          </div>
        ) : (
          <MapContainer
            center={DJERBA_CENTER}
            zoom={11}
            scrollWheelZoom
            style={{ height: "70vh", width: "100%" }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {hotels.map((h) => (
              <Marker key={h.id} position={[h.latitude!, h.longitude!]} icon={hotelIcon}>
                <Popup>
                  <div className="space-y-1">
                    <p className="flex items-center gap-1.5 font-semibold">
                      <Building2 className="size-3.5" /> {h.name}
                    </p>
                    <p className="text-muted-foreground">
                      {h.city}, {h.country}
                    </p>
                    <Badge variant={hotelStatusVariant[h.status]}>
                      {humanize(h.status)}
                    </Badge>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        )}
      </Card>
    </div>
  );
}
