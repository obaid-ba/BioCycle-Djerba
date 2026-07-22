import "leaflet/dist/leaflet.css";

import L from "leaflet";
import { Building2, Factory, MapPinOff } from "lucide-react";
import { useMemo } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer } from "react-leaflet";

import type { CollectionRequest } from "@/types";

const HOTEL_COLOR = "hsl(142 71% 40%)";
const PLANT_COLOR = "hsl(24 95% 53%)";

/**
 * CSS-based marker, matching MapView — avoids Leaflet's default PNG icons whose
 * bundler-broken image paths are a well-known footgun.
 */
function dotIcon(color: string): L.DivIcon {
  return L.divIcon({
    className: "",
    html: `<span style="display:block;width:16px;height:16px;border-radius:9999px;background:${color};border:2px solid white;box-shadow:0 0 0 1px rgba(0,0,0,.25)"></span>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

const hotelIcon = dotIcon(HOTEL_COLOR);
const plantIcon = dotIcon(PLANT_COLOR);

interface RequestRouteMapProps {
  request: CollectionRequest;
  /** Map height; the dialog wants it compact. */
  height?: string;
}

/**
 * Operator view of one request's geography: the declaring hotel, the
 * biomethanization plant, and the straight-line leg between them.
 *
 * The distance label reuses the request's `distance_to_plant_km`, snapshotted
 * server-side at creation, rather than recomputing it client-side — so what the
 * operator reads here is exactly the value the queue ranked on.
 */
export function RequestRouteMap({ request, height = "260px" }: RequestRouteMapProps) {
  const hotel = request.hotel;
  const { plant_latitude: plantLat, plant_longitude: plantLng } = request;

  const plant = useMemo<[number, number]>(
    () => [plantLat, plantLng],
    [plantLat, plantLng],
  );

  const hotelPos = useMemo<[number, number] | null>(
    () =>
      hotel?.latitude != null && hotel.longitude != null
        ? [hotel.latitude, hotel.longitude]
        : null,
    [hotel],
  );

  // Fit both points; Leaflet needs a non-degenerate box, and padding keeps the
  // markers off the edges.
  const bounds = useMemo(
    () => (hotelPos ? L.latLngBounds([hotelPos, plant]).pad(0.35) : null),
    [hotelPos, plant],
  );

  if (!hotelPos) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-2 rounded-md border border-dashed text-center"
        style={{ height }}
      >
        <MapPinOff className="size-5 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          {hotel
            ? `${hotel.name} has no coordinates yet.`
            : "No hotel attached to this request."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="overflow-hidden rounded-md border">
        <MapContainer
          bounds={bounds!}
          scrollWheelZoom={false}
          style={{ height, width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <Polyline
            positions={[hotelPos, plant]}
            pathOptions={{ color: PLANT_COLOR, weight: 3, dashArray: "6 6" }}
          />

          <Marker position={hotelPos} icon={hotelIcon}>
            <Popup>
              <p className="flex items-center gap-1.5 font-semibold">
                <Building2 className="size-3.5" /> {hotel!.name}
              </p>
              <p className="text-muted-foreground">
                {hotel!.address ? `${hotel!.address}, ` : ""}
                {hotel!.city}
              </p>
            </Popup>
          </Marker>

          <Marker position={plant} icon={plantIcon}>
            <Popup>
              <p className="flex items-center gap-1.5 font-semibold">
                <Factory className="size-3.5" /> Biomethanization plant
              </p>
            </Popup>
          </Marker>
        </MapContainer>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-3 text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full" style={{ background: HOTEL_COLOR }} />
            {hotel!.name}
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full" style={{ background: PLANT_COLOR }} />
            Plant
          </span>
        </div>
        {request.distance_to_plant_km != null && (
          <span className="font-medium tabular-nums">
            {request.distance_to_plant_km.toFixed(1)} km
            <span className="ml-1 font-normal text-muted-foreground">
              straight line
            </span>
          </span>
        )}
      </div>
    </div>
  );
}
