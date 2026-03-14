# Arguzz Fuzzer for SP1

## SP1 Resources
  - https://docs.succinct.xyz/docs/sp1/introduction
  - https://github.com/succinctlabs/sp1

```bash
sp1-fuzzer install --zkvm ./sp1 --commit-or-branch latticevm
sp1-fuzzer run --fault-injection -o output -z ./sp1 -l arguzz-x-sp1.log -v2
```
