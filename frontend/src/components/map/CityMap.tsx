import { type FC, useState, useCallback, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Popup,
  useMap,
  Rectangle,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { LatLngBoundsExpression, Map as LeafletMap } from "leaflet";
import type { CityGraphResponse, NodeSchema, EdgeSchema } from "@/types/api";
import { ROAD_STATUS_COLOUR, bboxToLeafletBounds, BLR_CENTRE } from "@/utils/geo";
import { formatDistance, formatDuration, formatPercent } from "@/utils/formatting";
import styles from "./CityMap.module.css";

// ── Fit-to-area control ────────────────────────────────────────────────────────

interface FitControlProps {
  bounds: LatLngBoundsExpression;
}

const FitControl: FC<FitControlProps> = ({ bounds }) => {
  const map = useMap();
  return (
    <button
      id="map-fit-area-btn"
      className={styles["fit-btn"]}
      style={{ position: "absolute", bottom: 24, right: 10, zIndex: 1000 }}
      onClick={() => map.fitBounds(bounds, { padding: [20, 20] })}
      title="Fit map to Bengaluru Urban district"
    >
      ⊡ Fit area
    </button>
  );
};

// ── Layer visibility state ─────────────────────────────────────────────────────

interface LayerState {
  roads: boolean;
  hospitals: boolean;
  disruptions: boolean;
  bbox: boolean;
}

// ── Popup content for edges ────────────────────────────────────────────────────

const EdgePopup: FC<{ edge: EdgeSchema }> = ({ edge }) => (
  <div className={styles["map-tooltip"]}>
    <div className={styles["map-tooltip__title"]}>
      Road Segment
      <span
        className={`${styles["road-status"]} ${styles[`road-status--${edge.status}`]}`}
        style={{ marginLeft: 8 }}
      >
        {edge.status}
      </span>
    </div>
    <div className={styles["map-tooltip__row"]}>
      <span className={styles["map-tooltip__key"]}>Type</span>
      <span className={styles["map-tooltip__val"]}>{edge.road_type}</span>
    </div>
    <div className={styles["map-tooltip__row"]}>
      <span className={styles["map-tooltip__key"]}>Length</span>
      <span className={styles["map-tooltip__val"]}>{formatDistance(edge.length_m)}</span>
    </div>
    <div className={styles["map-tooltip__row"]}>
      <span className={styles["map-tooltip__key"]}>Speed</span>
      <span className={styles["map-tooltip__val"]}>{edge.speed_kmh.toFixed(0)} km/h</span>
    </div>
    <div className={styles["map-tooltip__row"]}>
      <span className={styles["map-tooltip__key"]}>Travel time</span>
      <span className={styles["map-tooltip__val"]}>{formatDuration(edge.travel_time_s)}</span>
    </div>
    <div className={styles["map-tooltip__row"]}>
      <span className={styles["map-tooltip__key"]}>Flood risk</span>
      <span className={styles["map-tooltip__val"]}>{formatPercent(edge.flood_risk, 0)}</span>
    </div>
    {edge.confidence != null && (
      <div className={styles["map-tooltip__row"]}>
        <span className={styles["map-tooltip__key"]}>Confidence</span>
        <span className={styles["map-tooltip__val"]}>{formatPercent(edge.confidence, 0)}</span>
      </div>
    )}
    <div style={{ marginTop: 6, fontSize: "0.62rem", color: "var(--color-text-muted)" }}>
      Disruption score is inferred, not an observed water depth.
    </div>
  </div>
);

// ── Node popup ─────────────────────────────────────────────────────────────────

const NodePopup: FC<{ node: NodeSchema }> = ({ node }) => (
  <div className={styles["map-tooltip"]}>
    <div className={styles["map-tooltip__title"]}>
      {node.node_type === "hospital" ? "🏥 Hospital node" :
       node.node_type === "facility" ? "🔧 Facility node" : "⬡ Intersection"}
    </div>
    <div className={styles["map-tooltip__row"]}>
      <span className={styles["map-tooltip__key"]}>Node ID</span>
      <span className={styles["map-tooltip__val"]} style={{ fontSize: "0.65rem" }}>
        {node.node_id}
      </span>
    </div>
    <div className={styles["map-tooltip__row"]}>
      <span className={styles["map-tooltip__key"]}>Lat</span>
      <span className={styles["map-tooltip__val"]}>{node.lat.toFixed(5)}</span>
    </div>
    <div className={styles["map-tooltip__row"]}>
      <span className={styles["map-tooltip__key"]}>Lon</span>
      <span className={styles["map-tooltip__val"]}>{node.lon.toFixed(5)}</span>
    </div>
  </div>
);

// ── Main CityMap ───────────────────────────────────────────────────────────────

interface CityMapProps {
  graphData: CityGraphResponse | null;
  isLoading?: boolean;
}

const CityMap: FC<CityMapProps> = ({ graphData, isLoading = false }) => {
  const [layers, setLayers] = useState<LayerState>({
    roads: true,
    hospitals: true,
    disruptions: true,
    bbox: true,
  });

  const toggleLayer = useCallback(
    (key: keyof LayerState) =>
      setLayers((prev) => ({ ...prev, [key]: !prev[key] })),
    [],
  );

  const bbox = graphData?.metadata.bbox;
  const blrBounds: LatLngBoundsExpression = bbox
    ? bboxToLeafletBounds(bbox)
    : bboxToLeafletBounds({
        min_lat: 12.75,
        min_lon: 77.35,
        max_lat: 13.18,
        max_lon: 77.85,
      });

  // Build a node lookup map for edge rendering
  const nodeMap = new Map<string, NodeSchema>();
  graphData?.nodes.forEach((n) => nodeMap.set(n.node_id, n));

  // Separate hospitals for special rendering
  const hospitalNodes = graphData?.nodes.filter(
    (n) => n.node_type === "hospital" || n.node_type === "facility",
  ) ?? [];

  // Classify edges
  const openEdges = graphData?.edges.filter((e) => e.status === "OPEN") ?? [];
  const degradedEdges = graphData?.edges.filter((e) => e.status === "DEGRADED") ?? [];
  const closedEdges = graphData?.edges.filter((e) => e.status === "CLOSED") ?? [];

  function edgePositions(edge: EdgeSchema): [number, number][] | null {
    const src = nodeMap.get(edge.source_node);
    const tgt = nodeMap.get(edge.target_node);
    if (!src || !tgt) return null;
    return [
      [src.lat, src.lon],
      [tgt.lat, tgt.lon],
    ];
  }

  return (
    <div className={styles["map-wrapper"]}>
      {/* Layer controls */}
      <div className={styles["layer-controls"]}>
        {(
          [
            { key: "roads" as const, label: "Roads", color: "#22c55e" },
            { key: "hospitals" as const, label: "Facilities", color: "#06b6d4" },
            { key: "disruptions" as const, label: "Disruptions", color: "#ef4444" },
            { key: "bbox" as const, label: "District", color: "#3b82f6" },
          ] as const
        ).map(({ key, label, color }) => (
          <button
            key={key}
            id={`map-layer-${key}`}
            className={`${styles["layer-btn"]} ${layers[key] ? styles["layer-btn--active"] : ""}`}
            onClick={() => toggleLayer(key)}
            aria-pressed={layers[key]}
          >
            <span
              className={styles["layer-btn__dot"]}
              style={{ background: layers[key] ? color : "var(--color-border-strong)" }}
              aria-hidden="true"
            />
            {label}
          </button>
        ))}
      </div>

      {/* Map */}
      <MapContainer
        className={styles["map-container"]}
        center={BLR_CENTRE}
        zoom={11}
        zoomControl={true}
        attributionControl={true}
      >
        {/* OpenStreetMap basemap — OSM tile usage policy applies */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          subdomains="abcd"
          maxZoom={19}
        />

        {/* District bounding box */}
        {layers.bbox && (
          <Rectangle
            bounds={blrBounds}
            pathOptions={{
              color: "#3b82f6",
              weight: 2,
              fillOpacity: 0.03,
              dashArray: "6 4",
            }}
          />
        )}

        {/* Open roads */}
        {layers.roads &&
          openEdges.map((edge) => {
            const pos = edgePositions(edge);
            if (!pos) return null;
            return (
              <Polyline
                key={edge.edge_id}
                positions={pos}
                pathOptions={{
                  color: ROAD_STATUS_COLOUR.OPEN,
                  weight: 2,
                  opacity: 0.45,
                }}
              >
                <Popup><EdgePopup edge={edge} /></Popup>
              </Polyline>
            );
          })}

        {/* Disrupted roads */}
        {layers.disruptions &&
          degradedEdges.map((edge) => {
            const pos = edgePositions(edge);
            if (!pos) return null;
            return (
              <Polyline
                key={edge.edge_id}
                positions={pos}
                pathOptions={{
                  color: ROAD_STATUS_COLOUR.DEGRADED,
                  weight: 3,
                  opacity: 0.85,
                  dashArray: "8 4",
                }}
              >
                <Popup><EdgePopup edge={edge} /></Popup>
              </Polyline>
            );
          })}

        {layers.disruptions &&
          closedEdges.map((edge) => {
            const pos = edgePositions(edge);
            if (!pos) return null;
            return (
              <Polyline
                key={edge.edge_id}
                positions={pos}
                pathOptions={{
                  color: ROAD_STATUS_COLOUR.CLOSED,
                  weight: 4,
                  opacity: 0.95,
                }}
              >
                <Popup><EdgePopup edge={edge} /></Popup>
              </Polyline>
            );
          })}

        {/* Hospital / facility nodes */}
        {layers.hospitals &&
          hospitalNodes.map((node) => (
            <CircleMarker
              key={node.node_id}
              center={[node.lat, node.lon]}
              radius={node.node_type === "hospital" ? 8 : 6}
              pathOptions={{
                color: node.node_type === "hospital" ? "#06b6d4" : "#f59e0b",
                weight: 2,
                fillOpacity: 0.8,
                fillColor:
                  node.node_type === "hospital" ? "#0e7490" : "#92400e",
              }}
            >
              <Popup><NodePopup node={node} /></Popup>
            </CircleMarker>
          ))}

        <FitControl bounds={blrBounds} />
      </MapContainer>

      {/* Legend */}
      <div className={styles.legend} aria-label="Map legend">
        <div className={styles["legend__title"]}>Road Status</div>
        {(
          [
            { status: "OPEN", label: "Open" },
            { status: "DEGRADED", label: "Degraded" },
            { status: "CLOSED", label: "Closed" },
          ] as const
        ).map(({ status, label }) => (
          <div key={status} className={styles["legend__row"]}>
            <span
              className={styles["legend__swatch"]}
              style={{ background: ROAD_STATUS_COLOUR[status] }}
              aria-hidden="true"
            />
            <span className={styles["legend__label"]}>{label}</span>
          </div>
        ))}
        <div className={styles["legend__title"]} style={{ marginTop: 8 }}>
          Facilities
        </div>
        <div className={styles["legend__row"]}>
          <span
            className={`${styles["legend__swatch"]} ${styles["legend__swatch--circle"]}`}
            style={{ color: "#06b6d4", width: 10, height: 10 }}
            aria-hidden="true"
          />
          <span className={styles["legend__label"]}>Hospital</span>
        </div>
        <div className={styles["legend__row"]}>
          <span
            className={`${styles["legend__swatch"]} ${styles["legend__swatch--circle"]}`}
            style={{ color: "#f59e0b", width: 10, height: 10 }}
            aria-hidden="true"
          />
          <span className={styles["legend__label"]}>Facility</span>
        </div>
      </div>

      {/* Loading overlay */}
      {isLoading && (
        <div className={styles["map-overlay"]} aria-live="polite">
          <div
            style={{
              width: 24,
              height: 24,
              border: "2px solid var(--color-border)",
              borderTopColor: "var(--color-accent)",
              borderRadius: "50%",
              animation: "spin 0.7s linear infinite",
            }}
            aria-hidden="true"
          />
          Loading graph…
        </div>
      )}
    </div>
  );
};

export default CityMap;
