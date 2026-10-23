// Lookup tables from data keys to icon components (kept out of icons.jsx so
// that file only exports components, which React fast refresh needs).
import {
  FoodIcon,
  LifebuoyIcon,
  MedkitIcon,
  ShelterIcon,
  TruckIcon,
} from "./icons";

export const RESOURCE_ICONS = {
  rescue_teams: LifebuoyIcon,
  medical_kits: MedkitIcon,
  food_packets: FoodIcon,
  shelters: ShelterIcon,
  vehicles: TruckIcon,
};
