import asyncio
from typing import Optional
from src.management.settings import get_settings
from src.management.logger import configure_logger

settings = get_settings()
logger = configure_logger("AmneziaConnection", "blue")


class DockerError(Exception):
    pass


class AmneziaConnection:
    def __init__(self, container_name: Optional[str] = None):
        self.container_name = container_name or settings.amnezia_container_name
        self.interface = settings.amnezia_interface
        self.config_path = settings.amnezia_config_path

    async def run_command(self, cmd: str, check: bool = True) -> tuple[str, str]:
        full_cmd = ["docker", "exec", self.container_name, "sh", "-c", cmd]
        logger.debug(f"Executing: {' '.join(full_cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            logger.error("Docker executable not found. Ensure Docker is installed in the API container.")
            raise DockerError("Docker executable not found")
        except Exception as exc:
            logger.error(f"Failed to initiate docker command: {exc}")
            raise DockerError(f"Docker command initiation failed: {exc}")

        stdout, stderr = await process.communicate()
        stdout_decoded = stdout.decode().strip()
        stderr_decoded = stderr.decode().strip()

        if check and process.returncode != 0:
            logger.error(
                f"Command failed with code {process.returncode}: {stderr_decoded}"
            )
            raise DockerError(
                f"Command failed: {stderr_decoded or 'Unknown error'}"
            )

        return stdout_decoded, stderr_decoded

    async def read_file(self, path: str) -> str:
        stdout, _ = await self.run_command(f"cat {path}")
        return stdout

    async def write_file(self, path: str, content: str) -> None:
        escaped_content = content.replace("'", "'\\''")
        cmd = f"cat > {path} <<'EOF'\n{escaped_content}\nEOF"
        await self.run_command(cmd)
        logger.debug(f"File written: {path}")

    async def get_wg_dump(self) -> str:
        stdout, _ = await self.run_command(f"wg show {self.interface} dump")
        return stdout

    async def sync_wg_config(self) -> None:
        config_file = f"{self.config_path}/{self.interface}.conf"
        cmd = f"wg syncconf {self.interface} <(wg-quick strip {config_file})"
        await self.run_command(cmd)
        logger.info(f"WireGuard config synchronized for {self.interface}")

    async def read_wg_config(self) -> str:
        config_file = f"{self.config_path}/{self.interface}.conf"
        return await self.read_file(config_file)

    async def write_wg_config(self, content: str) -> None:
        config_file = f"{self.config_path}/{self.interface}.conf"
        await self.write_file(config_file, content)
        logger.info(f"WireGuard config written to {config_file}")

    async def generate_private_key(self) -> str:
        stdout, _ = await self.run_command("wg genkey")
        return stdout

    async def generate_public_key(self, private_key: str) -> str:
        cmd = f"echo '{private_key}' | wg pubkey"
        stdout, _ = await self.run_command(cmd)
        return stdout

    async def read_server_public_key(self) -> str:
        key_file = f"{self.config_path}/wireguard_server_public_key.key"
        return await self.read_file(key_file)

    async def read_preshared_key(self) -> str:
        key_file = f"{self.config_path}/wireguard_psk.key"
        return await self.read_file(key_file)
