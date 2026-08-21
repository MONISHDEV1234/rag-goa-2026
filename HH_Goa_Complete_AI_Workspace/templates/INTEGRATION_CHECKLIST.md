# INTEGRATION CHECKLIST

## Documentation
- [ ] `RULES.md` read
- [ ] Full `README.md` reviewed where required
- [ ] `ARCHITECTURE.md` reviewed
- [ ] `ROLES.md` reviewed
- [ ] All three role progress logs reviewed

## Interfaces
- [ ] Shared Pydantic schemas match
- [ ] Role 1 retrieval interface works
- [ ] Role 2 transcript/voice interface works
- [ ] Role 3 orchestration consumes both correctly

## Reliability
- [ ] Timeouts configured
- [ ] Transient retry behavior verified
- [ ] Missing context handled
- [ ] Off-topic/safety behavior verified
- [ ] Grounding behavior verified

## Performance
- [ ] Stage timings captured
- [ ] P50 calculated
- [ ] P70 calculated
- [ ] P100 calculated
- [ ] Total latency measured
- [ ] No samples were misleadingly excluded

## Final verification
- [ ] End-to-end smoke test passes
- [ ] No secrets/debug artifacts
- [ ] Progress logs updated
- [ ] Handoff/integration notes recorded
