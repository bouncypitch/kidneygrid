# KidneyGrid film — script & storyboard (≈84 s, 1920×1080, 30 fps)

Tone: quiet, human, hopeful. Soft piano under everything; one swell at the match.
All people are fictional (labelled "Dramatization"); all statistics are verified (sources on the end card).

| Time | Picture (Remotion scene) | Voiceover (read slowly; ~130 wpm) |
|---|---|---|
| 0:00–0:09 | **Stakes.** Plum background. A counter rolls up to **95,492**. Caption: "people in the US are waiting for a kidney." | "Right now, more than ninety-five thousand people in America are waiting for a kidney." |
| 0:09–0:27 | **Maria.** Two circles, *Tom* and *Maria*. A line tries to connect them and breaks with a ✕. Captions: "Maria has waited 7 years." · "Her husband Tom wants to give her his kidney." · "He can't. Wrong blood type." Tag: *Dramatization*. | "Maria has waited seven years. Her husband, Tom, would give her his kidney tomorrow. But he can't. Wrong blood type. At least one in three willing donors is the wrong match." |
| 0:27–0:42 | **Islands.** Five hospitals drift apart, each with a lock. Caption: "The right match exists — at another hospital." · "But hospitals can't share patient data." | "The right match for Maria exists. It's just at another hospital. And hospitals can't share patient records." |
| 0:42–1:08 | **KidneyGrid.** Hub-and-node network. Anonymous tokens travel out and back. Counters: Alone **0** → First-come **3** → KidneyGrid **5**. Green loops draw. Caption: "An agent in every hospital. Only anonymous yes/no answers leave." | "KidneyGrid puts an AI agent inside every hospital. The agents share only anonymous yes-or-no answers. Together, they find loops of swaps no hospital could find alone. Zero matches alone. Five together." |
| 1:08–1:24 | **Match & close.** Card: "Sam → Maria · 7 years waiting · Matched." Then: "No patient record left any hospital." · "Five families. Built on Flower." · **KidneyGrid** wordmark · sources. | "Sam, a stranger, gives Maria a kidney, so that his own partner receives one. Five families. And not one patient record ever left its hospital. KidneyGrid. Built on Flower." |

## Production
1. `cd video/remotion && npm install && npx remotion render KidneyGridFilm out/kidneygrid.mp4`
2. Voiceover: record the right-hand column (quiet room, phone/Mac mic, ~20 cm away), save as `video/remotion/public/voiceover.mp3`, then render with `--props='{"voiceover":true}'`.
3. Music: a royalty-free soft piano track (YouTube Audio Library / Pixabay Music), saved as `public/music.mp3`, render with `--props='{"voiceover":true,"music":true}'`.
4. Opener cut for the pitch (≈40 s): `npx remotion render KidneyGridOpener out/opener.mp4`.
5. Optional: replace the animated demo scene with a real screen capture of the web app (QuickTime → File → New Screen Recording), saved as `public/demo.mp4`, render with `"demoFootage": true`.

End-card sources: OPTN via organdonor.gov (July 2026); Segev et al., JAMA 2005. People shown are fictional; data simulated.
