#!/usr/bin/env python3
"""
AutoClip Studio - Main Entry Point
JSON-RPC over stdin/stdout for communication with WPF frontend.
"""

import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from auto_clip_studio.services.video_processor import VideoProcessor
from auto_clip_studio.services.transcription_service import TranscriptionService
from auto_clip_studio.services.clip_selector import ClipSelector
from auto_clip_studio.services.layout_renderer import LayoutRenderer
from auto_clip_studio.services.subtitle_generator import SubtitleGenerator
from auto_clip_studio.services.download_service import DownloadService
from auto_clip_studio.models.job import Job, JobStatus, JobProgress
from auto_clip_studio.utils.logger import setup_logging
from auto_clip_studio.utils.config import Config

# Setup logging
logger = logging.getLogger(__name__)

class AutoClipStudioRPC:
    """JSON-RPC handler for WPF communication."""

    def __init__(self, config: Config):
        self.config = config
        self.video_processor = VideoProcessor(config)
        self.transcription_service = TranscriptionService(config)
        self.clip_selector = ClipSelector(config)
        self.layout_renderer = LayoutRenderer(config)
        self.subtitle_generator = SubtitleGenerator(config)
        self.download_service = DownloadService(config)
        self.current_job: Optional[Job] = None

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "download_video":
                result = await self._download_video(params)
            elif method == "transcribe":
                result = await self._transcribe(params)
            elif method == "select_clips":
                result = await self._select_clips(params)
            elif method == "render_clips":
                result = await self._render_clips(params)
            elif method == "generate_subtitles":
                result = await self._generate_subtitles(params)
            elif method == "get_job_status":
                result = await self._get_job_status(params)
            elif method == "cancel_job":
                result = await self._cancel_job(params)
            elif method == "validate_url":
                result = await self._validate_url(params)
            elif method == "get_available_layouts":
                result = await self._get_available_layouts(params)
            elif method == "preview_layout":
                result = await self._preview_layout(params)
            elif method == "correct_subtitle":
                result = await self._correct_subtitle(params)
            elif method == "export_clip":
                result = await self._export_clip(params)
            else:
                raise ValueError(f"Unknown method: {method}")

            return {"jsonrpc": "2.0", "result": result, "id": request_id}

        except Exception as e:
            logger.exception(f"Error handling {method}")
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": request_id
            }

    async def _download_video(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = params["url"]
        output_dir = Path(params.get("output_dir", self.config.temp_dir))
        topic = params.get("topic")

        self.current_job = Job.create_download_job(url, output_dir, topic)
        self.current_job.status = JobStatus.DOWNLOADING

        async for progress in self.download_service.download(url, output_dir, topic):
            self.current_job.progress = progress
            await self._emit_progress(self.current_job)

        self.current_job.status = JobStatus.DOWNLOADED
        await self._emit_progress(self.current_job)

        return {
            "video_path": str(self.current_job.video_path),
            "audio_path": str(self.current_job.audio_path),
            "metadata": self.current_job.metadata,
            "duration": self.current_job.duration
        }

    async def _transcribe(self, params: Dict[str, Any]) -> Dict[str, Any]:
        audio_path = Path(params["audio_path"])
        language = params.get("language", "es")
        model_size = params.get("model_size", "large-v3")

        self.current_job = Job.create_transcription_job(audio_path, language, model_size)
        self.current_job.status = JobStatus.TRANSCRIBING

        async for progress in self.transcription_service.transcribe(audio_path, language, model_size):
            self.current_job.progress = progress
            await self._emit_progress(self.current_job)

        self.current_job.status = JobStatus.TRANSCRIBED
        await self._emit_progress(self.current_job)

        return {
            "segments": self.current_job.transcription_segments,
            "words": self.current_job.transcription_words,
            "language": self.current_job.detected_language
        }

    async def _select_clips(self, params: Dict[str, Any]) -> Dict[str, Any]:
        transcription = params["transcription"]
        video_duration = params["video_duration"]
        topic = params.get("topic")
        max_clips = params.get("max_clips", 3)
        max_duration = params.get("max_duration", 75)

        self.current_job = Job.create_selection_job(transcription, video_duration, topic, max_clips, max_duration)
        self.current_job.status = JobStatus.SELECTING

        async for progress in self.clip_selector.select_clips(
            transcription, video_duration, topic, max_clips, max_duration
        ):
            self.current_job.progress = progress
            await self._emit_progress(self.current_job)

        self.current_job.status = JobStatus.SELECTED
        await self._emit_progress(self.current_job)

        return {"clips": self.current_job.selected_clips}

    async def _render_clips(self, params: Dict[str, Any]) -> Dict[str, Any]:
        clips = params["clips"]
        video_path = Path(params["video_path"])
        layout = params.get("layout", "solo_podcast")
        background_path = params.get("background_path")
        output_dir = Path(params.get("output_dir", self.config.output_dir))

        self.current_job = Job.create_render_job(clips, video_path, layout, background_path, output_dir)
        self.current_job.status = JobStatus.RENDERING

        async for progress in self.layout_renderer.render_clips(
            clips, video_path, layout, background_path, output_dir
        ):
            self.current_job.progress = progress
            await self._emit_progress(self.current_job)

        self.current_job.status = JobStatus.RENDERED
        await self._emit_progress(self.current_job)

        return {"rendered_clips": self.current_job.rendered_clips}

    async def _generate_subtitles(self, params: Dict[str, Any]) -> Dict[str, Any]:
        clip = params["clip"]
        words = params["words"]
        style = params.get("style", "karaoke")

        subtitles = await self.subtitle_generator.generate(clip, words, style)
        return {"subtitles": subtitles}

    async def _get_job_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self.current_job:
            return self.current_job.to_dict()
        return {"status": "idle"}

    async def _cancel_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self.current_job:
            self.current_job.cancel()
            return {"cancelled": True}
        return {"cancelled": False, "reason": "No active job"}

    async def _validate_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = params["url"]
        result = await self.download_service.validate_url(url)
        return result

    async def _get_available_layouts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        layouts = self.layout_renderer.get_available_layouts()
        return {"layouts": layouts}

    async def _preview_layout(self, params: Dict[str, Any]) -> Dict[str, Any]:
        layout = params["layout"]
        clip = params.get("clip")
        preview_path = await self.layout_renderer.generate_preview(layout, clip)
        return {"preview_path": str(preview_path)}

    async def _correct_subtitle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        clip_id = params["clip_id"]
        word_index = params["word_index"]
        corrected_text = params["corrected_text"]
        time_offset = params.get("time_offset", 0.0)

        result = await self.subtitle_generator.correct_word(clip_id, word_index, corrected_text, time_offset)
        return result

    async def _export_clip(self, params: Dict[str, Any]) -> Dict[str, Any]:
        clip = params["clip"]
        output_path = Path(params["output_path"])
        subtitles = params.get("subtitles")

        final_path = await self.video_processor.export_final_clip(clip, output_path, subtitles)
        return {"output_path": str(final_path)}

    async def _emit_progress(self, job: Job):
        """Emit progress notification to WPF."""
        notification = {
            "jsonrpc": "2.0",
            "method": "progress",
            "params": job.to_dict()
        }
        print(json.dumps(notification), flush=True)


async def main():
    """Main entry point - reads JSON-RPC from stdin, writes responses to stdout."""
    config = Config.load()
    setup_logging(config.log_level)

    rpc = AutoClipStudioRPC(config)

    logger.info("AutoClip Studio Python backend started")

    # Read JSON-RPC requests from stdin
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break

        line = line.decode("utf-8").strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            response = await rpc.handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    asyncio.run(main())