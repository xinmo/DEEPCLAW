import React from 'react';
import AppLayout from './components/Layout/AppLayout';
import DocumentParsePage from './pages/DocumentParsePage';
import './styles/global.css';

const App: React.FC = () => {
  return (
    <AppLayout>
      <DocumentParsePage />
    </AppLayout>
  );
};

export default App;
