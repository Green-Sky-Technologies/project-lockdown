/** Host lookup — hosts are data (design doc §3). Adding a chatbot is one config. */
import { chatgpt } from './chatgpt';
import { claude } from './claude';
import { gemini } from './gemini';
import type { HostConfig } from './types';

const CONFIGS: HostConfig[] = [chatgpt, claude, gemini];

export function hostConfigFor(host: string): HostConfig | null {
  return CONFIGS.find((c) => host === c.host || host.endsWith(`.${c.host}`)) ?? null;
}
