import React, { useState, useEffect } from 'react';
import AppLayout from './components/Layout/AppLayout';
import DocumentParsePage from './pages/DocumentParsePage';
import RealtimeTranslatePage from './pages/RealtimeTranslatePage';
import KnowledgeBasePage from './pages/KnowledgeBasePage';
import KnowledgeChatPage from './pages/KnowledgeChatPage';
import ClawChatPage from './pages/ClawChatPage';
import PromptManagementPage from './pages/PromptManagementPage';
import './styles/global.css';

const App: React.FC = () => {
  // 从 localStorage 恢复上次的页面，默认为文档解析页面
  const [currentPage, setCurrentPage] = useState(() => {
    return localStorage.getItem('javisagent_current_page') || 'document-parse';
  });

  // 当页面切换时，保存到 localStorage
  useEffect(() => {
    localStorage.setItem('javisagent_current_page', currentPage);
  }, [currentPage]);

  const renderPage = () => {
    switch (currentPage) {
      case 'document-parse':
        return <DocumentParsePage />;
      case 'realtime-translate':
        return <RealtimeTranslatePage />;
      case 'knowledge-base':
        return <KnowledgeBasePage />;
      case 'knowledge-chat':
        return <KnowledgeChatPage />;
      case 'claw-chat':
        return <ClawChatPage />;
      case 'prompt-management':
        return <PromptManagementPage />;
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
