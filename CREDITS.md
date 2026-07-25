# Credits & Acknowledgements

## Conceptual foundation

hivemind's **knowledge-compounding model** is adapted from **AgentOps — "The Science"** by
[`boshu2`](https://github.com/boshu2/agentops) (Apache-2.0). That work is where this project's
core thesis comes from. Specifically, the following are AgentOps' ideas, not hivemind's:

- the knowledge-dynamics equation **`dK/dt = I(t) − δ·K + σ·ρ·K`**;
- the **escape-velocity** condition **`σ·ρ > δ/100`** (knowledge compounds when retrieval outruns decay);
- the **σ / ρ / δ** decomposition — retrieval **coverage**, retrieval **usage**, and knowledge **decay**;
- **MemRL** utility re-ranking (utility-scored retrieval that learns from what gets used);
- the **40% context rule** (load only what's relevant; performance peaks well below full context);
- the validation-**ratchet** metaphor (gates make progress one-way).

**hivemind is an independent implementation of these ideas — it contains no AgentOps code.** It is a
from-scratch Python/FastMCP server and Claude Code customization stack that operationalizes the model
above. Credit for the *model* belongs to AgentOps.

- The Science: <https://boshu2.github.io/agentops/the-science/>
- Repository: <https://github.com/boshu2/agentops> (Apache-2.0)

### A note on one reframing

hivemind presents **ρ as retrieval *precision*** — how *useful* the notes it surfaces turn out to be.
AgentOps defines ρ more precisely as the **decision-influence / citation rate** (the fraction of
surfaced artifacts later used or cited). hivemind's framing is a simplification for a developer
audience; the underlying quantity is the same signal.

## Foundational research (as synthesized by AgentOps)

AgentOps' model rests on prior academic work. hivemind leans on the following directly; full citations
and the complete bibliography live in AgentOps' "The Science" page.

- **Ebbinghaus, H. (1885).** *Memory: A Contribution to Experimental Psychology.* — the forgetting
  curve; the empirical basis for treating knowledge as something that **decays** without reinforcement (δ).
- **Darr, E. D., Argote, L., & Epple, D. (1995).** "The Acquisition, Transfer, and Depreciation of
  Knowledge in Service Organizations." *Management Science.* — organizational knowledge depreciation;
  source of the **~17%/week decay rate** that anchors δ.
- **Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., & Liang, P. (2023).**
  "Lost in the Middle: How Language Models Use Long Contexts." arXiv:[2307.03172](https://arxiv.org/abs/2307.03172)
  (TACL 2023). — long-context utilization degrades in the middle; the empirical backing for the **40% context rule**.
- **"MemRL: Self-Evolving Agents via Runtime Reinforcement Learning on Episodic Memory" (2026).**
  arXiv:[2601.03192](https://arxiv.org/abs/2601.03192). — two-phase retrieval that filters candidates by
  semantic relevance and then selects by learned utility (Q-values). hivemind's **fusion → MemRL re-rank**
  pipeline mirrors this structure.

AgentOps' "The Science" also draws on Miller (1956) and Cowan (2001) on working-memory capacity,
Sweller (1988) on cognitive load, Csikszentmihalyi (1990) on flow, Kim et al. (2016) *The DevOps
Handbook*, and Meadows (2008) *Thinking in Systems*. See its bibliography for the full set and links.

## License note

AgentOps is licensed Apache-2.0. Because hivemind includes **none of its code**, this file is an
acknowledgement of intellectual inspiration rather than a code-license (NOTICE) obligation. hivemind
itself is released under the [MIT License](LICENSE).
