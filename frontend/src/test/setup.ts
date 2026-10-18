import "@testing-library/jest-dom";
import { vi } from "vitest";

// Mock leaflet for tests (it requires DOM APIs not available in jsdom)
vi.mock("leaflet", () => ({
  default: {
    map: vi.fn(),
    tileLayer: vi.fn(),
    marker: vi.fn(),
    polyline: vi.fn(),
    divIcon: vi.fn(),
    latLngBounds: vi.fn(),
    icon: vi.fn(),
  },
}));

vi.mock("react-leaflet", () => ({
  MapContainer: vi.fn(() => null),
  TileLayer: vi.fn(() => null),
  Marker: vi.fn(() => null),
  Polyline: vi.fn(() => null),
  Popup: vi.fn(() => null),
  LayerGroup: vi.fn(() => null),
  useMap: vi.fn(),
  CircleMarker: vi.fn(() => null),
  Rectangle: vi.fn(() => null),
  ZoomControl: vi.fn(() => null),
}));
