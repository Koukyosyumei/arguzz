import os
from pathlib import Path

from zkvm_fuzzer_utils.cmd import ExecStatus, invoke_command
from zkvm_fuzzer_utils.file import path_to_binary

CARGO = path_to_binary("cargo")
RUSTUP = path_to_binary("rustup")
# `+toolchain` directives are only handled by the rustup cargo proxy, not by a
# direct cargo binary. Resolve the proxy that lives next to the rustup binary
# so toolchain-pinned commands work even if a non-rustup cargo comes first on PATH.
RUSTUP_CARGO = str(Path(RUSTUP).parent / "cargo") if RUSTUP else CARGO


# ---------------------------------------------------------------------------- #
#                             Cargo Command Builder                            #
# ---------------------------------------------------------------------------- #


class CargoCmd:
    __cargo: str
    __action: str

    __release: bool = False
    __force: bool = False
    __locked: bool = False
    __explicit_clean_zombies: bool = False
    __toolchain: str | None = None
    __environment: dict[str, str] | None = None
    __binary: str | None = None
    __arguments: list[str] | None = None
    __path: Path | None = None
    __cwd: Path | None = None
    __timeout: float | None = None
    __sub_cli: str | None = None

    def __init__(self, action: str):
        self.__cargo = CARGO
        self.__action = action

    @classmethod
    def build(cls) -> "CargoCmd":
        return CargoCmd("build")

    @classmethod
    def run(cls) -> "CargoCmd":
        return CargoCmd("run")

    @classmethod
    def install(cls) -> "CargoCmd":
        return CargoCmd("install")

    @classmethod
    def clean(cls) -> "CargoCmd":
        return CargoCmd("clean")

    def in_release(self) -> "CargoCmd":
        self.__release = True
        return self

    def with_toolchain(self, toolchain: str) -> "CargoCmd":
        self.__toolchain = toolchain
        return self

    def with_env(self, environment: dict[str, str]) -> "CargoCmd":
        if self.__environment is None:
            self.__environment = {}
        for key, value in environment.items():
            if key in self.__environment:
                raise RuntimeError(f"try to set multiple environment keys for {key}!")
            else:
                self.__environment[key] = value
        return self

    def with_rustflags(self, value_str: str) -> "CargoCmd":
        return self.with_env({"RUSTFLAGS": value_str})

    def with_coverage(self) -> "CargoCmd":
        return self.with_rustflags("-C instrument-coverage")

    def with_bin(self, binary: str) -> "CargoCmd":
        self.__binary = binary
        return self

    def with_args(self, arguments: list[str]) -> "CargoCmd":
        self.__arguments = arguments
        return self

    def use_force(self) -> "CargoCmd":
        self.__force = True
        return self

    def use_locked(self) -> "CargoCmd":
        self.__locked = True
        return self

    def with_path(self, path: Path) -> "CargoCmd":
        self.__path = path
        return self

    def with_cd(self, cwd: Path) -> "CargoCmd":
        self.__cwd = cwd
        return self

    def with_timeout(self, timeout: float) -> "CargoCmd":
        self.__timeout = timeout
        return self

    def with_explicit_clean_zombies(self) -> "CargoCmd":
        self.__explicit_clean_zombies = True
        return self

    def with_sub_cli(self, name: str) -> "CargoCmd":
        self.__sub_cli = name
        return self

    def get_command(self) -> list[str]:
        if self.__toolchain:
            command = [RUSTUP_CARGO, f"+{self.__toolchain}"]
        else:
            command = [self.__cargo]
        if self.__sub_cli:
            command.append(self.__sub_cli)
        command.append(self.__action)
        if self.__release:
            command.append("--release")
        if self.__force:
            command.append("--force")
        if self.__locked:
            command.append("--locked")
        if self.__path:
            command += ["--path", f"{self.__path}"]
        if self.__binary:
            command += ["--bin", f"{self.__binary}"]
        if self.__arguments:
            command += ["--"] + self.__arguments
        return command

    def execute(self) -> ExecStatus:
        env = self.__environment
        # When a toolchain is requested, ensure the rustup proxy directory is
        # first on PATH for the subprocess. cargo subcommands (e.g. cargo-pico)
        # spawn nested `cargo +<toolchain> ...` calls via PATH lookup, and a
        # non-rustup cargo cannot resolve the `+toolchain` directive.
        if self.__toolchain and RUSTUP:
            rustup_dir = str(Path(RUSTUP).parent)
            existing_path = (env or {}).get("PATH") or os.environ.get("PATH", "")
            path_entries = existing_path.split(os.pathsep) if existing_path else []
            if not path_entries or path_entries[0] != rustup_dir:
                env = dict(env) if env else {}
                env["PATH"] = f"{rustup_dir}{os.pathsep}{existing_path}"
        return invoke_command(
            self.get_command(),
            env=env,
            cwd=self.__cwd,
            timeout=self.__timeout,
            explicit_clean_zombies=self.__explicit_clean_zombies,
        )


# ---------------------------------------------------------------------------- #
