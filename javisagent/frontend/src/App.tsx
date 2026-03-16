import React, { useEffect, useState } from "react";

import AppLayout from "./components/Layout/AppLayout";
import ChannelsPage from "./pages/ChannelsPage";
import ClawChatPage from "./pages/ClawChatPage";
import ClawSkillsPage from "./pages/ClawSkillsPage";
import DocumentParsePage from "./pages/DocumentParsePage";
import KnowledgeBasePage from "./pages/KnowledgeBasePage";
import KnowledgeChatPage from "./pages/KnowledgeChatPage";
import PromptManagementPage from "./pages/PromptManagementPage";
import RealtimeTranslatePage from "./pages/RealtimeTranslatePage";
import "./styles/global.css";

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState(() => {
    return localStorage.getItem("javisagent_current_page") || "document-parse";
  });

  useEffect(() => {
    localStorage.setItem("javisagent_current_page", currentPage);
  }, [currentPage]);

  const renderPage = () => {
    switch (currentPage) {
      case "document-parse":
        return <DocumentParsePage />;
      case "realtime-translate":
        return <RealtimeTranslatePage />;
      case "knowledge-base":
        return <KnowledgeBasePage />;
      case "knowledge-chat":
        return <KnowledgeChatPage />;
      case "claw-chat":
        return <ClawChatPage />;
      case "claw-skills":
        return <ClawSkillsPage />;
      case "prompt-management":
        return <PromptManagementPage />;
      case "channel-qq":
        return <ChannelsPage initialChannel="qq" />;
      default:
        return <DocumentParsePage />;
    }
  };

  return (
    <AppLayout onMenuSelect={setCurrentPage} selectedKey={currentPage}>
      {renderPage()}
    </AppLayout>
  );
};

export default App;
