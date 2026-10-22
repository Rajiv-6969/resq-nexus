// Lookup tables from data keys to icon components (kept out of icons.jsx so
// that file only exports components, which React fast refresh needs).
import {
  FlameIcon,
  FoodIcon,
  LifebuoyIcon,
  MedkitIcon,
  QuakeIcon,
  ShelterIcon,
  TruckIcon,
  WavesIcon,
} from "./icons";

export const RESOURCE_ICONS = {
  rescue_teams: LifebuoyIcon,
  medical_kits: MedkitIcon,
  food_packets: FoodIcon,
  shelters: ShelterIcon,
  vehicles: TruckIcon,
};

export const DISASTER_ICONS = { flood: WavesIcon, earthquake: QuakeIcon, wildfire: FlameIcon };
