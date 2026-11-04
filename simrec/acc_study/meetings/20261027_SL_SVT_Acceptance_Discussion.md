## Key Outcomes

Provakar presented early results from an acceptance study for a forward disk tracker, revealing that the current fractional acceptance plots are unreliable due to a poorly defined denominator (eta range too narrow) and an inadequate straight-line projection method for missing hits. Shujie recommended a new approach: plotting the **phi vs. eta distribution of MC particles associated with actual hits** on each disk at Z=0 to establish a natural acceptance map, which will then serve as a well-grounded denominator for future binned acceptance studies. The straight-line projection issue is acknowledged but deprioritized until the acceptance map reveals whether there are significant coverage gaps worth investigating further.

---

## Decisions Made

- **Primary next step:** Generate phi vs. eta distributions of MC particles (retrieved via hit-particle association) for each disk individually, starting with Z=0 and 1 GeV pions, to map natural acceptance boundaries rather than imposing an arbitrary eta cut. 
- **Denominator definition deferred:** The current fractional acceptance plots (e.g., showing ED4 with apparently low acceptance) are considered artifacts of the incorrect eta range used as denominator and should not be interpreted as real physics. 
- **Straight-line projection improvement deprioritized:** Adding a sensitive surface in front of/behind each disk to capture missing hit locations is a valid solution but will only be pursued if the acceptance map reveals a significant problem. 
- **AI tool:** Provakar to continue using Codex (GPT-4o 5.6) for code generation; Shujie suggested using Claude as well, but Provakar is satisfied with current tooling for this project. 

---

## Feedback Exchanged

- **On the acceptance fraction plots:** Shujie noted the denominator is the core issue — for barrel detectors the natural acceptance edge is well-defined and translatable to an eta value, but for disks this is not straightforward and requires empirical determination from the data itself. 
- **On the eta cut choice:** **Provakar's eta range of 0.922 to 2** was flagged by Shujie as too narrow, causing the large apparent hole in disk plots (e.g., disk 4); the correct range should span the full disk coverage. 
- **On the RMS projection quality:** Even at high momenta (**p ∈ [10, 20] GeV**), the straight-line projection RMS is poor and degrades further at larger distances from the vertex — confirming it is unsuitable for bin-by-bin acceptance work in a non-dipole magnetic field. 
- **On AI supervision:** Shujie emphasized the importance of actively reviewing AI-generated code to catch silent assumptions or errors, noting that AI tools can move too fast and make unjustified assumptions. 
- **On slides:** Shujie reviewed Provakar's presentation slides and found them satisfactory; advised raising any open questions during the AIC meeting to capture Ernst's attention given his busy schedule around an upcoming review. 

---

## Proposed Acceptance Mapping Methodology (Detail)

The agreed workflow replaces the current approach with the following steps:

- **Step 1 — Hit retrieval:** For each disk surface, collect all hits registered on that surface. 
- **Step 2 — Particle association:** Retrieve the MC primary particle associated with each hit (using the existing hit-particle association framework already in place). 
- **Step 3 — 2D distribution:** Plot **phi vs. eta** of those associated particles to visualize the natural geometric acceptance of each disk. 
- **Step 4 — Condition as denominator:** Use the resulting eta-phi acceptance region as the selection condition for the denominator in all future binned acceptance fraction studies, replacing the arbitrary eta range. 
- **Scope:** Loop over all disk combinations, starting with Z=0 vertex and 1 GeV pions; extend to other Z values (±10 cm) and momentum ranges afterward. 
- **Tooling:** Shujie suggested using Claude to write the for-loop automation to iterate over all momentum and disk combinations and save output plots for page-by-page review. 

---

## Simulation Dataset Status

- **Events generated:** ~30 million total events across three vertex positions (Z = 0, +10, −10 cm), produced in ~3 hours using the premium QoS partition with efficient node/core utilization. 
- **Momentum range:** **p ∈ [0.5, 20] GeV** continuous spectrum. 
- **Eta range:** **η ∈ [0.6, 3.8]** and **η ∈ [−3.8, −0.6]**, providing flexibility to apply any eta cut in post-processing. 
- **Vertex locations:** **Z = 0, ±10** cm. 
- **Job structure:** 100,000 events/job × 50 jobs per vertex location ≈ 10 million events/vertex; additional statistics can be appended easily via existing job IDs without re-running analysis. 
- **Current assessment:** Statistics are sufficient for the immediate next steps; no additional generation needed until 1 GeV beam studies are initiated. 

---

## Blockers

- **Magnetic field projection:** The helical (non-dipole) magnetic field makes straight-line projection of MC particles to disk surfaces unreliable, especially at low momentum — this prevents accurate bin-by-bin acceptance calculation without either a field map integration or additional sensitive detector surfaces. 
- **Undefined denominator:** Without a well-motivated eta-phi boundary per disk, fractional acceptance plots cannot be interpreted physically; this is the primary blocker for producing publishable acceptance results. 

---

## Pending Confirmation

- Whether adding zero-material sensitive surfaces immediately in front of and behind each disk in the Geant4 simulation is worth implementing — deferred until acceptance map reveals significant missing-hit regions. 
- Ernst's feedback on the current study; he has gone silent after initial questions were answered, and Shujie confirmed he wants to see the acceptance study results. 
- Optimal eta-phi ranges per disk — to be determined empirically from the phi vs. eta hit maps rather than assumed a priori. 

---

## Open Questions

- **η range 1.0–2.8 or 1.0–2.6** for HD0 coverage — Shujie indicated the existing detector layout plots may be outdated and disk geometry near the beam pipe may be placeholder-only, so empirical mapping is preferred over relying on design documents. 
- Whether momentum-binned acceptance maps are needed from the start or whether an integrated-momentum map is sufficient as a first pass — left open, to be revisited after the Z=0, 1 GeV baseline plots are produced. 

---

## Action Items

- **Provakar:** For each disk, plot phi vs. eta of MC particles associated with hits, starting with Z=0 vertex and 1 GeV pions, then loop over all disk and momentum combinations; save all plots for review. 
- **Provakar:** Use Claude (or Codex) to write the for-loop automation for the above scan across all disk/momentum/vertex combinations. 
- **Provakar:** Share updated acceptance maps with Shujie before deciding whether to implement additional sensitive detector surfaces. 
- **Provakar:** Raise any open acceptance study questions at the AIC meeting to get Ernst's input while he is present. 

---

## Next 1:1

No specific date scheduled; Shujie asked Provakar to reconnect once the phi vs. eta acceptance maps are produced. Both were joining the NSD Colloquium immediately after this call. 
