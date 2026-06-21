import { useRef, useState, type ChangeEvent, type KeyboardEvent } from "react";
import { PaperclipIcon, SendIcon } from "./icons";

interface ComposerProps {
  disabled: boolean;
  onSend: (text: string) => void;
  onFiles: (files: FileList) => void;
}

export function Composer({ disabled, onSend, onFiles }: ComposerProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function autoGrow() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }

  function onChange(e: ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value);
    autoGrow();
  }

  function submit() {
    const q = text.trim();
    if (!q || disabled) return;
    onSend(q);
    setText("");
    requestAnimationFrame(autoGrow);
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function onPick(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files?.length) onFiles(e.target.files);
    e.target.value = ""; // allow re-picking the same file
  }

  return (
    <div className="flex items-end gap-2 rounded-2xl border border-edge bg-panel-2 px-2.5 py-2 focus-within:border-accent/60 focus-within:ring-2 focus-within:ring-accent/20">
      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.docx,.txt"
        multiple
        className="hidden"
        onChange={onPick}
      />
      <button
        title="Attach a document"
        onClick={() => fileRef.current?.click()}
        className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-fog transition hover:bg-panel-3 hover:text-white"
      >
        <PaperclipIcon width={18} height={18} />
      </button>

      <textarea
        ref={textareaRef}
        rows={1}
        value={text}
        onChange={onChange}
        onKeyDown={onKey}
        placeholder="Ask about your industry reports…"
        className="max-h-[200px] flex-1 resize-none bg-transparent py-1.5 text-sm text-white outline-none placeholder:text-fog-2"
      />

      <button
        title="Send"
        onClick={submit}
        disabled={disabled || !text.trim()}
        className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-accent text-white transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-40"
      >
        <SendIcon width={17} height={17} />
      </button>
    </div>
  );
}
