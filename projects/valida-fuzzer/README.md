# Arguzz Fuzzer for Valida

## Valida Resources
  - https://docs.succinct.xyz/docs/valida/introduction
  - https://github.com/succinctlabs/valida

```bash
valida-fuzzer install --zkvm ./valida-vm --commit-or-branch a13377060607ed3463cc17a7c8d005a9fe492b03
valida-fuzzer run --fault-injection -o output -z ./valida-vm -l arguzz-x-valida.log -v2
```

