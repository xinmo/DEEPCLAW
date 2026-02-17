import React, { useState } from 'react';
import AppLayout from './components/Layout/AppLayout';
import DocumentParsePage from './pages/DocumentParsePage';
import RealtimeTranslatePage from './pages/RealtimeTranslatePage';
import KnowledgeBasePage from './pages/KnowledgeBasePage';
import KnowledgeChatPage from './pages/KnowledgeChatPage';
import './styles/global.css';

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState('document-parse');

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
