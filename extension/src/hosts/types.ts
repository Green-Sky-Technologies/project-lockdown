/**
 * A host adapter is DATA, not a code branch (design doc §3): adding a chatbot is
 * one config object, the capture logic is shared. Selectors are the fragile part
 * of any DOM-scraping capture and are expected to be maintained over time.
 */
export interface HostConfig {
  /** location.host this config applies to, e.g. "chatgpt.com". */
  host: string;
  /** The composer input (textarea or contenteditable) the user types into. */
  inputSelector: string;
  /** Optional explicit "send" button, in addition to Enter-to-send. */
  sendButtonSelector?: string;
  /** Rendered conversation turns, used to scrape assistant context. */
  turnSelector?: string;
  /** Classify a turn element as user/assistant (null = ignore). */
  roleFor?(el: Element): 'user' | 'assistant' | null;
}
