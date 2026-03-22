import React, { Suspense, lazy, useEffect, useState } from "react";
import { Button, Spin } from "antd";

import AppLayout from "./components/Layout/AppLayout";
import { CLAW_STREAM_STATUS_EVENT, type ClawStreamStatusDetail } from "./constants/clawChat";
import "./styles/global.css";

const ClawChatPage = lazy(() => import("./pages/ClawChatPage"));
const ChannelsPage = lazy(() => import("./pages/ChannelsPage"));
const ClawMcpPage = lazy(() => import("./pages/ClawMcpPage"));
const ClawSkillsPage = lazy(() => import("./pages/ClawSkillsPage"));
const DocumentParsePage = lazy(() => import("./pages/DocumentParsePage"));
const IndustryResearchPage = lazy(() => import("./pages/IndustryResearchPage"));
const KnowledgeBasePage = lazy(() => import("./pages/KnowledgeBasePage"));
const KnowledgeChatPage = lazy(() => import("./pages/KnowledgeChatPage"));
const PromptManagementPage = lazy(() => import("./pages/PromptManagementPage"));
const RealtimeTranslatePage = lazy(() => import("./pages/RealtimeTranslatePage"));

const EMPTY_CLAW_STREAM_STATUS: ClawStreamStatusDetail = {
  sending: false,
  conversationId: null,
  conversationTitle: null,
};

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState(() => {
    return localStorage.getItem("javisagent_current_page") || "document-parse";
  });
  const [hasOpenedClawChat, setHasOpenedClawChat] = useState(() => currentPage === "claw-chat");
  const [clawStreamStatus, setClawStreamStatus] = useState<ClawStreamStatusDetail>(EMPTY_CLAW_STREAM_STATUS);

  useEffect(() => {
    localStorage.setItem("javisagent_current_page", currentPage);
  }, [currentPage]);

  useEffect(() => {
    const handleClawStreamStatus = (event: Event) => {
      const detail = (event as CustomEvent<ClawStreamStatusDetail>).detail;
      if (!detail) {
        return;
      }
      setClawStreamStatus(detail);
    };

    window.addEventListener(CLAW_STREAM_STATUS_EVENT, handleClawStreamStatus as EventListener);
    return () => {
      window.removeEventListener(CLAW_STREAM_STATUS_EVENT, handleClawStreamStatus as EventListener);
    };
  }, []);

  const handlePageSelect = (nextPage: string) => {
    if (nextPage === "claw-chat") {
      setHasOpenedClawChat(true);
    }
    setCurrentPage(nextPage);
  };

  const renderNonClawPage = () => {
    switch (currentPage) {
      case "document-parse":
        return <DocumentParsePage />;
      case "realtime-translate":
        return <RealtimeTranslatePage />;
      case "knowledge-base":
        return <KnowledgeBasePage />;
      case "knowledge-chat":
        return <KnowledgeChatPage />;
      case "claw-skills":
        return <ClawSkillsPage />;
      case "prompt-management":
        return <PromptManagementPage />;
      case "channel-qq":
        return <ChannelsPage initialChannel="qq" />;
      case "mcp-management":
        return <ClawMcpPage />;
      case "industry-research":
        return <IndustryResearchPage />;
      default:
        return <DocumentParsePage />;
    }
  };

  const shouldRenderClawChatHost = hasOpenedClawChat || currentPage === "claw-chat";
  const showBackgroundClawStatus = currentPage !== "claw-chat" && clawStreamStatus.sending;
  const backgroundClawLabel = clawStreamStatus.conversationTitle
    ? `Claw is still processing "${clawStreamStatus.conversationTitle}"`
    : "Claw is still processing the current conversation";
  const pageFallback = (
    <div
      style={{
        minHeight: "70vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Spin size="large" tip="Loading workspace..." />
    </div>
  );

  return (
    <AppLayout onMenuSelect={handlePageSelect} selectedKey={currentPage}>
      <>
        {shouldRenderClawChatHost ? (
          <div
            style={{
              display: currentPage === "claw-chat" ? "block" : "none",
              height: "100%",
            }}
          >
            <Suspense fallback={pageFallback}>
              <ClawChatPage active={currentPage === "claw-chat"} />
            </Suspense>
          </div>
        ) : null}
        {currentPage === "claw-chat" ? null : <Suspense fallback={pageFallback}>{renderNonClawPage()}</Suspense>}
        {showBackgroundClawStatus ? (
          <Button
            type="primary"
            onClick={() => handlePageSelect("claw-chat")}
            style={{
              position: "fixed",
              right: 32,
              bottom: 32,
              zIndex: 1200,
              height: "auto",
              padding: "10px 14px",
              borderRadius: 999,
              boxShadow: "0 12px 28px rgba(22, 119, 255, 0.24)",
            }}
          >
            {`${backgroundClawLabel}. Open chat for progress.`}
          </Button>
        ) : null}
      </>
    </AppLayout>
  );
};

export default App;
