import { useOutletContext } from "react-router-dom";
import type { AppOutletContext } from "./AppLayout";
import { PlusIcon } from "./icons";

export function Welcome() {
  const { newConversation } = useOutletContext<AppOutletContext>();
  return (
    <div className="grid h-full place-items-center px-4 text-center">
      <div>
        <div className="iq-grad mx-auto mb-5 grid h-16 w-16 place-items-center rounded-2xl text-xl font-bold text-white shadow-[0_0_36px_-6px_var(--color-accent)]">
          IQ
        </div>
        <h1 className="text-2xl font-semibold text-white">Welcome to IndustryIQ</h1>
        <p className="mx-auto mt-2 max-w-md text-sm text-fog">
          Start a conversation to chat with your industry reports. Drag in a PDF, DOCX, or TXT any
          time to ground answers in your own documents.
        </p>
        <button
          onClick={() => void newConversation()}
          className="mt-6 inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-strong"
        >
          <PlusIcon width={16} height={16} /> New chat
        </button>
      </div>
    </div>
  );
}
