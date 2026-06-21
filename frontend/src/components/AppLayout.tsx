import { useCallback, useEffect, useState } from "react";
import { Outlet, useMatch, useNavigate } from "react-router-dom";
import * as api from "../api";
import type { ConversationSummary } from "../api";
import { Sidebar } from "./Sidebar";

// Shared with the routed children (Welcome / ChatView) via <Outlet context>.
export interface AppOutletContext {
  refreshConversations: () => Promise<void>;
  renameConversation: (id: string, title: string) => Promise<void>;
  newConversation: () => Promise<void>;
}

export function AppLayout() {
  const navigate = useNavigate();
  // A layout route can't read a child route's :id via useParams, so match the
  // chat path directly to know which conversation is active in the sidebar.
  const activeId = useMatch("/c/:id")?.params.id;
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setConversations(await api.listConversations());
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const newConversation = useCallback(async () => {
    setBusy(true);
    try {
      const c = await api.createConversation();
      await refresh();
      navigate(`/c/${c.id}`);
    } finally {
      setBusy(false);
    }
  }, [navigate, refresh]);

  const renameConversation = useCallback(
    async (id: string, title: string) => {
      await api.renameConversation(id, title);
      await refresh();
    },
    [refresh],
  );

  const deleteConversation = useCallback(
    async (id: string) => {
      await api.deleteConversation(id);
      await refresh();
      if (id === activeId) navigate("/");
    },
    [activeId, navigate, refresh],
  );

  const context: AppOutletContext = { refreshConversations: refresh, renameConversation, newConversation };

  return (
    <div className="flex h-full">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        busy={busy}
        onNew={() => void newConversation()}
        onSelect={(id) => navigate(`/c/${id}`)}
        onRename={(id, title) => void renameConversation(id, title)}
        onDelete={(id) => void deleteConversation(id)}
      />
      <main className="min-w-0 flex-1">
        <Outlet context={context} />
      </main>
    </div>
  );
}
