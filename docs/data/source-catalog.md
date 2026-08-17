# Renewable Development Intelligence
## Public Data Source Catalog

**Scope:** V1 western Oklahoma / SPP wind-development screening

---

## Access Classes

- **A — Machine accessible:** API, REST service, public cloud object store, CSV, or direct download.
- **B — Public document/web source:** accessible publicly but primarily HTML/PDF/document oriented.
- **C — Human or authenticated workflow:** public process, but requires interactive/login/submission activity.
- **D — Developer/proprietary input:** unavailable or inappropriate to infer from public sources.

---

# 1. Wind Resource

## WIND-001 — HRRR MET Toolkit

**Authority:** DOE / Open Energy Data Initiative / National Laboratory wind program  
**Role:** Primary V1 candidate for screening-level wind meteorology  
**Access:** A  
**Format:** Public AWS S3 / structured meteorological data  
**Geography:** CONUS  
**Resolution:** approximately 2-km horizontal grid; hourly  
**Temporal coverage:** 2015-present with planned extensions

Public S3:

https://nrel-pds-wtk.s3.amazonaws.com/

S3 prefix:

s3://nrel-pds-wtk/hrrr_met_toolkit/

### Potential V1 use

- wind-speed statistics;
- directional characteristics;
- temporal profiles;
- hub-height screening inputs where supported;
- resource variability.

### Important limitation

This is screening-level modeled meteorological evidence.

It is not a bankable wind-resource assessment or bankable AEP.

### Status

**ACCESS SPIKE REQUIRED**

---

## WIND-002 — WIND Toolkit Long-Term Ensemble Dataset

**Authority:** DOE / OEDI  
**Role:** Candidate supplementary long-term wind-resource dataset  
**Access:** A  
**Format:** Public AWS S3 / structured data

S3 prefix:

s3://nrel-pds-wtk/wtk-led/

### Potential V1 use

Potential comparison/validation source where longer-period climatology is valuable.

### Status

**DEFER until WIND-001 spike is understood**

---

# 2. SPP Interconnection Queue

## SPP-QUEUE-001 — Active Generator Interconnection Requests

**Authority:** Southwest Power Pool  
**Access:** A  
**Format:** CSV

Human-readable listing:

https://opsportal.spp.org/Studies/GIActive

CSV endpoint:

https://opsportal.spp.org/Studies/GenerateActiveCSV

### Expected fields include

- generation interconnection number;
- current cluster;
- county/town;
- state;
- transmission owner at POI;
- proposed dates;
- capacity MW;
- generation type;
- fuel type;
- substation or line;
- request received date;
- status;
- associated studies.

### V1 use

Deterministic queue analytics:

- Oklahoma requests;
- wind requests;
- MW concentration;
- POI/substation patterns;
- queue status;
- age;
- COD timing;
- nearby/relevant development activity.

### Limitation

Queue presence does not establish available transmission capacity or project-specific interconnection cost.

### Status

**VERIFIED PUBLIC — ACCESS SPIKE REQUIRED**

---

# 3. SPP Interconnection Studies

## SPP-STUDY-001 — Generator Interconnection Studies

**Authority:** Southwest Power Pool  
**Access:** B/A  
**Format:** HTML listings + downloadable study documents

Study index:

https://opsportal.spp.org/Studies/Gen

### Study categories include

- impact studies;
- facility studies;
- affected-system studies;
- historical feasibility studies;
- other posted GI studies.

### V1 use

Agentic investigation:

- locate relevant studies;
- retrieve study documents;
- identify network constraints;
- identify network upgrades;
- identify affected facilities;
- identify related projects;
- follow evidence across studies.

### Processing model

Document retrieval + RAG + agent interpretation.

Do not reduce this source to only deterministic table parsing.

### Status

**VERIFIED PUBLIC — ACCESS SPIKE REQUIRED**

---

# 4. SPP Rules and Process Documents

## SPP-REG-001 — Generator Interconnection Procedures / Current SPP Process Documents

**Authority:** Southwest Power Pool / FERC-approved tariff framework  
**Access:** B  
**Format:** PDF / HTML / tariff documents

Starting point:

https://opsportal.spp.org/Studies/Gen

### V1 use

Regulatory/process knowledge corpus:

- applicable GI process;
- terminology;
- study stages;
- financial/security requirements where relevant;
- current process versus superseded process;
- CPP transition/current framework.

### Required metadata

- publication date;
- effective date;
- superseded date where known;
- document version;
- source hash.

### Status

**PUBLIC DOCUMENT CORPUS**

---

# 5. Terrain / Elevation

## GIS-ELEV-001 — USGS 3DEP

**Authority:** U.S. Geological Survey  
**Access:** A  
**Format:** Raster products / API-discovered downloads / web services

TNMAccess API documentation:

https://tnmaccess.nationalmap.gov/api/v1/docs

### V1 use

Deterministic:

- elevation;
- slope;
- terrain complexity;
- terrain-based exclusions or risk metrics.

### Processing

Rasterio / NumPy / GeoPandas / PyProj.

### Status

**VERIFIED API — ACCESS SPIKE REQUIRED**

---

# 6. Land Cover

## GIS-LC-001 — USGS Annual NLCD

**Authority:** U.S. Geological Survey  
**Access:** A  
**Format:** Raster / web services / AWS / downloads

Information:

https://www.usgs.gov/centers/eros/science/annual-national-land-cover-database

### V1 use

Screening of:

- developed land;
- cultivated crops;
- grassland;
- forest;
- wetlands classes;
- other material land-cover categories.

### Limitation

Land-cover classification is not equivalent to legal buildability or land control.

### Status

**VERIFIED PUBLIC — ENDPOINT SPIKE REQUIRED**

---

# 7. Wetlands

## ENV-WET-001 — National Wetlands Inventory

**Authority:** U.S. Fish & Wildlife Service  
**Access:** A  
**Format:** ArcGIS REST / WMS / downloadable GIS

REST root:

https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/

### V1 use

Deterministic GIS:

- wetland intersection;
- wetland acreage;
- wetland percentage;
- proximity/buffer analysis when justified.

### Limitation

NWI screening is not a jurisdictional wetlands determination.

### Status

**VERIFIED REST SERVICE — ACCESS SPIKE REQUIRED**

---

# 8. FEMA Flood Hazards

## ENV-FLOOD-001 — National Flood Hazard Layer

**Authority:** Federal Emergency Management Agency  
**Access:** A  
**Format:** ArcGIS REST / GIS data

REST service:

https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer

### V1 use

Deterministic GIS:

- flood-zone intersection;
- affected acreage;
- site-level screening;
- later infrastructure exposure.

### Limitation

Screening result is not a project-specific floodplain permit determination.

### Status

**VERIFIED REST SERVICE — ACCESS SPIKE REQUIRED**

---

# 9. Federally Listed Species

## ENV-ESA-001 — USFWS IPaC

**Authority:** U.S. Fish & Wildlife Service  
**Access:** C for official project species list

Portal:

https://ipac.ecosphere.fws.gov/

### V1 use

Official project-specific species evidence.

### V1 workflow

1. Agent determines that official species evidence is required.
2. Investigation enters HITL state.
3. Human creates/opens the IPaC project.
4. Human requests official species list.
5. Resulting document is supplied to the project.
6. Agent resumes analysis.
7. Document is retained as evidence.

### Important rule

General public species-location information must not be mislabeled as the official IPaC species list.

### Status

**HITL**

---

## ENV-ESA-002 — USFWS ECOS Data Services

**Authority:** U.S. Fish & Wildlife Service  
**Access:** A/B depending service

Data services:

https://ecos.fws.gov/ecp/services

### V1 use

Preliminary species/context investigation and supporting evidence.

### Status

**ACCESS SPIKE REQUIRED**

---

# 10. Protected Lands

## ENV-PAD-001 — PAD-US

**Authority:** U.S. Geological Survey  
**Access:** A  
**Format:** Downloadable GIS + web services

Information:

https://www.usgs.gov/programs/gap-analysis-project/science/pad-us-data-overview

### V1 use

Deterministic intersection with:

- public protected areas;
- refuges;
- wilderness;
- conservation lands;
- other protected-area designations.

### Important requirement

Protection category must be interpreted.

Intersection alone must not automatically mean the site is legally prohibited.

### Status

**VERIFIED PUBLIC — ENDPOINT SPIKE REQUIRED**

---

# 11. Cultural / Historic Screening

## ENV-NRHP-001 — National Register of Historic Places

**Authority:** National Park Service  
**Access:** A/B  
**Format:** ArcGIS REST / downloadable GIS / documents

REST service:

https://mapservices.nps.gov/arcgis/rest/services/cultural_resources/nrhp_locations/MapServer

### V1 use

Screening for known National Register resources near/intersecting project area.

### Limitation

Absence from the public dataset does not constitute Section 106 clearance.

### Status

**VERIFIED REST SERVICE — ACCESS SPIKE REQUIRED**

---

# 12. Oklahoma Wind Regulation

## OK-REG-001 — Oklahoma Corporation Commission Wind Energy Facilities

**Authority:** Oklahoma Corporation Commission  
**Access:** B  
**Format:** HTML / forms / filings / linked legal authorities

Starting point:

https://oklahoma.gov/occ/divisions/public-utility/energy/renewable-energy/ok-wind-farms-energy-facilities.html

### Relevant topics include

- notice to Corporation Commission;
- notice to county commissioners;
- mission compatibility;
- notice of intent to build;
- public meetings;
- commencement of construction;
- reporting requirements.

### V1 use

Agentic regulatory investigation.

### Processing model

RAG + rule/document interpretation + citations.

### Status

**VERIFIED PUBLIC**

---

# 13. Local / County Requirements

## OK-LOCAL-001 — County and Local Government Sources

**Authority:** Applicable county/local government  
**Access:** B/C — variable by county

### V1 use

Agent identifies counties intersecting candidate polygon and investigates current authoritative sources.

### Expected challenges

- inconsistent websites;
- PDFs;
- meeting records;
- zoning documents;
- lack of structured APIs.

### Rule

If authoritative requirements cannot be established:

`UNRESOLVED — HUMAN DILIGENCE REQUIRED`

The agent shall not infer a local ordinance from another county.

### Status

**DYNAMIC AGENT RESEARCH**

---

# 14. Aviation

## FAA-001 — FAA OE/AAA

**Authority:** Federal Aviation Administration  
**Access:** B/C  
**Format:** Web application / public search / formal submission workflow

Portal:

https://oeaaa.faa.gov/

### V1 use

Screening for:

- whether FAA diligence is likely required;
- nearby aviation considerations;
- existing/proposed case context where publicly available.

### Later-stage use

Turbine-specific submissions/determinations require formal project workflow.

### Rule

Agent output is not an FAA determination.

### Status

**HYBRID PUBLIC + HITL**

---

# 15. Military Compatibility

## OK-MIL-001 — Oklahoma OCC Mission Compatibility Evidence

**Authority:** Oklahoma Corporation Commission / applicable military review process  
**Access:** B/C

Starting point:

https://oklahoma.gov/occ/divisions/public-utility/energy/renewable-energy/ok-wind-farms-energy-facilities/mission-compatibility-letters.html

### V1 use

- identify requirement;
- identify precedent/examples;
- determine whether project-specific review is required.

### Rule

Do not infer project-specific compatibility from other projects' letters.

### Status

**PUBLIC EVIDENCE + PROJECT-SPECIFIC HITL**

---

# 16. Transmission Lines

## TRANS-001 — Public Electric Transmission Line GIS

**Authorities:** HIFLD-related public GIS / EIA-referenced source  
**Access:** A/B

### V1 use

Deterministic screening:

- nearest transmission line;
- approximate distance;
- nominal voltage where available;
- corridor density.

### Major limitation

Public line data is not an authoritative SPP power-flow model.

Public EIA/HIFLD references do not provide authoritative substation-location data suitable for treating a nearby point as an established POI.

### Status

**SOURCE ENDPOINT STILL TO BE LOCKED**

---

# 17. Candidate Project Polygon

## DEV-001 — Developer Candidate Area

**Authority:** Developer/user  
**Access:** D  
**Format:** GeoJSON initially

### Required

- geometry;
- CRS;
- project identifier.

### V1 source

User-supplied.

---

# 18. Land Control / Parcel Ownership

## DEV-002 — Parcels / Leases / Land Control

**Authority:** Developer / county records / commercial parcel provider  
**Access:** D/B depending county

### V1 position

Not required for initial MVP.

The candidate polygon represents the area under consideration, not confirmed land control.

### Future use

- parcel-level land control;
- lease status;
- ownership fragmentation;
- title constraints.

### Status

**OUT OF V1 CORE**

---

# 19. Source Selection Principle

For each business question:

1. Prefer authoritative source.
2. Prefer machine-accessible authoritative data for deterministic calculations.
3. Preserve raw retrieved evidence.
4. Record retrieval date/version.
5. Never substitute a convenient secondary source when an authoritative source is reasonably available.
6. Separate source facts from deterministic derivations and agent interpretations.
7. Escalate when required authoritative project-specific evidence cannot be obtained automatically.

