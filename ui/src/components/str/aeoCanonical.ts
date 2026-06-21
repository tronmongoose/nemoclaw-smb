/** Canonical Sweet Clementine AEO remediation artifacts.
 *
 * The HTTP AEO response (serve_aeo_call) returns the computed score, dimension
 * breakdown, optimized opening, and reasoning trace, but NOT the critical-flag
 * set or the JSON-LD block (those live on the dataclass, not the serialized
 * dict). These are the documented remediation outputs for the Clementine path,
 * mirrored here so the Platform view can render the dog-only CRITICAL conflict
 * and the proposed schema.org JSON-LD that the audit produces.
 *
 * Mirrors skills/aeo_skill.py _CLEMENTINE_FLAGS[0] and a slice of
 * _CLEMENTINE_JSON_LD. Kept in sync by hand; not on the live response path.
 */

export const DOG_ONLY_CRITICAL = {
  severity: "CRITICAL",
  code: "pet_species_conflict",
  message:
    "Listing intro reads 'pet-friendly home' with no species restriction. House rules read 'We only accept dogs.' Structured pet field shows petsAllowed=true with no species qualifier.",
  plain_english:
    "A cat owner reading the listing intro would believe cats are welcome. They would be turned away at the door. This conflict causes AI booking agents to misrepresent the pet policy to every traveler who asks.",
};

export const CLEMENTINE_JSON_LD = {
  "@context": "https://schema.org",
  "@type": "LodgingBusiness",
  name: "Sweet Clementine by the Sea",
  checkinTime: "16:00",
  checkoutTime: "11:00",
  petsAllowed: true,
  "x-str-pet-policy": {
    allowed: true,
    species: ["dogs"],
    maxCount: 2,
    feePerPetPerNight: 30,
    currency: "USD",
  },
  "x-str-permit": "018234",
};
