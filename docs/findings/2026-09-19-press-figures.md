# Which press figures hold up against their sources

**Date:** 2026-09-19 · **Area:** pitch (#15), README · **Checked by:** Bryan's session

CLAUDE.md and #15 require every press figure to be checked against its original source before it reaches the README, the UI or a slide. The sources are the ones listed in PLAN.md section 12.

| Figure | Verdict | Source, verbatim |
|---|---|---|
| The fire ran 3 km in 40 minutes | ✅ | Tribuna de Ávila, 23 Jul 2026: "3 kilómetros en 40 minutos"; Ávilared, 23 Jul: "tres kilómetros en 40 minutos" |
| 1,200–1,300 people evacuated from La Atalaya | ✅ | Tribuna de Ávila: "entre 1.200 y 1.300 personas"; Ávilared: "1.300 personas" |
| 1,500 evacuated in total | ✅ | Both: "1.500 evacuados" |
| 5 homes destroyed | ✅ | Tribuna de Ávila: "cinco viviendas"; Ávilared: "cinco casas quemadas" (La Atalaya) |
| About 250 people sheltered in El Barraco's sports hall | ✅ | Ávilared: "en torno a 250 se van a albergar en el polideportivo municipal de El Barraco" |
| More than 300 firefighters and staff | ✅ | Both: "más de 300 efectivos" |
| ES-Alert ordered **confinement** of El Tiemblo, Burgohondo and Navaluenga "due to the smoke" | ✅ | Ávilared (art. 93357), alert text: "Se procede a confinar las poblaciones de El Tiemblo, Burgohondo y Navaluenga debido al humo. Rogamos que permanezcan en sus domicilios." |
| 37,818 ha affected in Ávila (provisional) | ✅ | Ávilared (art. 93917), 21 Aug 2026, from the Junta de Castilla y León's Consejería de Medio Ambiente, measured on Sentinel images: "ha afectado provisionalmente a 37.818 hectáreas en la provincia de Ávila". Ávila only; the first estimate of 50,000 was revised down |
| 229 homes inside the burned perimeter, €47.5M market value, up to €21.4M to repair | ✅ as an estimate | Ávilared (art. 93518), 31 Jul 2026, "según estimaciones de Idealista" (Copernicus images crossed with the Catastro): "229 viviendas […] dentro del perímetro calcinado, aunque por el momento se desconoce el estado real"; "En el peor de los escenarios […] 21,4 millones de euros". Say "inside the burned area" and "worst case", never "destroyed" |
| €4M from the Junta for the area's environmental recovery | ✅ | Tribuna de Ávila, 3 Sep 2026: "eleva a 4 millones de euros el montante total destinado por el Gobierno Autonómico a la recuperación ambiental de la zona" |
| Tourism collapsed in high season | ✅ qualitative only | Ávilared (art. 93648), 10 Aug 2026, a local business owner: "un desplome de la actividad en plena temporada alta". No figure in euros or cancellations |
| People injured | ❌ Not verified | Not in the four articles checked. Do not state a number, or that there were none |
| 16 municipalities lost mobile coverage *in this fire* | ⚠️ Not as stated | The Objective, 29 Jul: "16 municipios y unos 40 núcleos de población quedaron inicialmente sin cobertura móvil o fija", in an article covering fires in Almería, Madrid and Ávila, with no breakdown by fire |
| "The largest fire in Spain" | ❌ Not found | Not in any of the four sources |
| A care home evacuated at night | ❌ Not found | Not in any of the four sources |
| More than 13,000 evacuated or confined | ❌ Not found | Not in any of the four sources |

## What we do about it

- The pitch script (`docs/demo/pitch.md`) uses only ✅ figures, each with its source.
- The README no longer calls it "the largest in Spain".
- PLAN.md section 2 still carries the ❌ figures; the team should correct or source them before the repo goes public (#16).
- For the coverage objection, say "in the late-July fires, 16 municipalities lost coverage, according to The Objective", not "in this fire".

## Sources

- https://avilared.com/art/93917/balance-incendio-burgohondo-37800-hectareas-afectadas-avila
- https://avilared.com/art/93518/incendio-burgohondo-riesgo-229-viviendas-valor-mercado-47-millones
- https://www.tribunaavila.com/noticias/457525/dos-millones-para-recuperar-las-zonas-afectadas-por-el-incendio-de-burgohondo
- https://avilared.com/art/93648/impacto-incendio-burgohondo-turismo-economia-el-burguillo

- https://www.tribunaavila.com/noticias/453214/el-incendio-de-burgohondo-deja-1-500-evacuados-y-arrasa-gran-parte-del-valle-iruelas
- https://avilared.com/art/93361/incendio-devastador-burgohondo-iruelas-1500-evacuados-cinco-casas-quemadas
- https://avilared.com/art/93357/alerta-esalert-confinamiento-el-tiemblo-burgohondo-navaluenga-incendio-forestal
- https://theobjective.com/tecnologia/2026-07-29/fallos-comunicacion-incendio-almeria-madrid-avila/
