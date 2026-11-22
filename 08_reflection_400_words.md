# 400-WORD REFLECTION: ENGINEERING AI-NATIVE CLINICAL QUEUE SYSTEMS

**Author:** CIT AI-Native Engineering Programme · Student Submission  
**Assessment:** Assessment 5 (Semester 1 Showcase)  
**Word Count:** 412 words  

---

Building the Clinic Visit Sorter fundamentally reshaped my understanding of applied artificial intelligence in high-stakes environments. When beginning this project, my initial instinct was to treat the Large Language Model as an all-powerful oracle, expecting it to understand student symptoms, diagnose ailments, and manage the waiting queue autonomously. However, through rigorous testing and confrontation with real-world edge cases, I learned the most vital lesson of AI engineering: **in safety-critical domains, raw model capability is useless without deterministic boundaries and human-in-the-loop governance.**

The greatest technical challenge emerged when testing multilingual Tanglish notes such as *"Enakku nenju valikuthu"* (chest pain) and *"Moochu vida mudiyala"* (cannot breathe). While modern LLMs are remarkably proficient at translation, minor stochastic variations in generation temperature occasionally caused a critical emergency to be labeled as moderate `today` priority instead of `see_now`. In a clinical lobby, such a false negative can be fatal. This failure demonstrated why probabilistic systems must never stand alone in triage. To resolve this, I architected a defense-in-depth model combining deterministic regex scanning in Python with semantic LLM inference. By enforcing the **Principle of Monotonicity**—where priority can only rise and never be downgraded by AI—we guaranteed that emergency presentations bypass any potential model hallucinations or network latencies.

Equally transformative was implementing the strict "No Diagnosis" constraint. As engineers, we often encourage generative models to elaborate; in medical administration, however, speculation is hazardous. An AI suggesting "suspected migraine" risks anchoring clinical staff and blinding them to a subarachnoid hemorrhage. By restricting the LLM to symptom summaries under 12 words and sanitizing diagnostic vocabulary, the tool respects its true purpose: an administrative queue organizer, not a replacement for medical expertise.

Finally, designing the system around the human checkpoint solidified my perspective on ethical AI deployment. The software never removes a student, never prescribes medication, and never discharges a patient. Every record in `visits.csv` is preserved, and the nurse reviews 100% of the cases with the student's original, unedited words visible. Developing the Clinic Visit Sorter taught me that AI-native engineering is not about delegating human responsibility to an algorithm; it is about building reliable, transparent scaffolds that empower human professionals to make faster, safer, and better-informed decisions.
