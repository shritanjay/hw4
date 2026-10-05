import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './auth'
import { ChatResultsProvider } from './chatResults'
import '@fontsource/eb-garamond/500.css'
import '@fontsource/eb-garamond/600.css'
import '@fontsource/eb-garamond/700.css'
import '@fontsource/eb-garamond/400-italic.css'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ChatResultsProvider>
          <App />
        </ChatResultsProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
