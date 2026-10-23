// Lookup tables from data keys to icon components (kept out of icons.jsx so
// that file only exports components, which React fast refresh needs).
import {
  BrainIcon,
  CpuIcon,
  FlameIcon,
  FoodIcon,
  GaugeIcon,
  LifebuoyIcon,
  MedkitIcon,
  QuakeIcon,
  RadarIcon,
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

export const PIPELINE_ICONS = { assess: RadarIcon, prioritise: GaugeIcon, allocate: CpuIcon, explain: BrainIcon };
