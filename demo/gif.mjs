// Converts the rendered MP4 into the README GIF: 1200 px wide, 15 fps, optimised palette, looping.
import { execFileSync } from "node:child_process";

const filters = "fps=15,scale=1200:-1:flags=lanczos";
execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", "out/supportpilot.mp4", "-vf", `${filters},palettegen=stats_mode=diff`, "out/palette.png"]);
execFileSync("ffmpeg", [
  "-y", "-loglevel", "error", "-i", "out/supportpilot.mp4", "-i", "out/palette.png",
  "-lavfi", `${filters}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle`,
  "-loop", "0", "out/supportpilot.gif",
]);
