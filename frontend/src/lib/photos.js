// Photographs bundled with the site (grayscale, cropped) and their credits.
import credits from "../assets/photos/credits.json";
import aboutPillars from "../assets/photos/about-concrete-pillars.jpg";
import cycloneFani from "../assets/photos/cyclone-fani-puri.jpg";
import damageCollapsed from "../assets/photos/damage-collapsed-building.jpg";
import earthquakeChautara from "../assets/photos/earthquake-chautara.jpg";
import floodAerial from "../assets/photos/flood-assam-aerial.jpg";
import heroAssembly from "../assets/photos/hero-chandigarh-assembly.jpg";
import reliefAssam from "../assets/photos/relief-assam-floods.jpg";
import wildfireAlmora from "../assets/photos/wildfire-almora.jpg";

const FILES = {
  "about-concrete-pillars": aboutPillars,
  "cyclone-fani-puri": cycloneFani,
  "damage-collapsed-building": damageCollapsed,
  "earthquake-chautara": earthquakeChautara,
  "flood-assam-aerial": floodAerial,
  "hero-chandigarh-assembly": heroAssembly,
  "relief-assam-floods": reliefAssam,
  "wildfire-almora": wildfireAlmora,
};

const shortAuthor = (author) => author.replace(/ from United States$/, "").replace(/^DFID - /, "");

export const PHOTO_LIST = credits.map((c) => ({ ...c, src: FILES[c.slug], credit: `${shortAuthor(c.author)} / ${c.license}` }));
export const PHOTOS = Object.fromEntries(PHOTO_LIST.map((p) => [p.slug, p]));

// One photograph per disaster type for scenario cards.
export const SCENARIO_PHOTOS = {
  flood: PHOTOS["flood-assam-aerial"],
  earthquake: PHOTOS["earthquake-chautara"],
  wildfire: PHOTOS["wildfire-almora"],
  cyclone: PHOTOS["cyclone-fani-puri"],
};
