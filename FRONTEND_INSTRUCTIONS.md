# Frontend Development Instructions for Module 10

## IMPORTANT: Use Context7 MCP for Professional UI

This project requires a PROFESSIONAL, MODERN frontend. Use Context7 MCP tools when available.

## Tech Stack (MANDATORY)

```bash
# Initialize with these exact tools
cd frontend
npm create vite@latest . -- --template react-ts
npm install @tanstack/react-query axios react-router-dom
npm install react-hook-form zod @hookform/resolvers
npm install zustand
npm install -D @types/react @types/react-dom tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Choose ONE component library:
# Option A: Shadcn/ui (Recommended)
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card input form toast

# Option B: Material-UI
npm install @mui/material @emotion/react @emotion/styled
```

## Project Structure (MANDATORY)

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/           # Shadcn/ui components
│   │   ├── layout/       # Header, Footer, Sidebar
│   │   └── common/       # Reusable components
│   ├── features/
│   │   ├── auth/         # Login, Register, Profile
│   │   ├── chat/         # Chat interface, Message list
│   │   ├── bots/         # Bot creation, management
│   │   └── admin/        # Admin dashboard
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useChat.ts
│   │   └── useApi.ts
│   ├── lib/
│   │   ├── api.ts        # Axios instance
│   │   ├── utils.ts      # Helper functions
│   │   └── constants.ts
│   ├── pages/            # Page components
│   ├── services/         # API service layer
│   ├── stores/           # Zustand stores
│   ├── types/            # TypeScript interfaces
│   └── styles/           # Global styles
```

## Design Requirements

### 1. Professional UI Elements
- ✅ Use card-based layouts with proper shadows and borders
- ✅ Implement skeleton loaders (not "Loading..." text)
- ✅ Use toast notifications for all actions
- ✅ Add smooth transitions (framer-motion optional)
- ✅ Implement proper error boundaries
- ✅ Use professional color scheme (not default blue/red)

### 2. Chat Interface Must Include
- Split panel design (sidebar for sessions, main for chat)
- Message bubbles with user/AI distinction
- Typing indicators
- Code syntax highlighting in messages
- Copy code button for code blocks
- Message timestamps
- Edit/Delete message options
- Session management in sidebar

### 3. Forms Must Have
- Inline validation with react-hook-form + zod
- Clear error messages
- Loading states on submit
- Success feedback
- Proper label and placeholder text
- Password strength indicators (for registration)

### 4. Responsive Design
- Mobile: Stack navigation, full-width components
- Tablet: Collapsible sidebar
- Desktop: Full sidebar, optimal spacing
- Test at: 320px, 768px, 1024px, 1440px

## API Integration

Backend API is at: `http://localhost:8220`

Create an API service layer:

```typescript
// src/lib/api.ts
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8220';

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

## Component Examples

### DON'T DO THIS (Amateur):
```jsx
<div>
  <h1>Chat</h1>
  <div>{messages.map(m => <p>{m.text}</p>)}</div>
  <input onChange={e => setText(e.target.value)} />
  <button onClick={send}>Send</button>
</div>
```

### DO THIS (Professional):
```tsx
<ChatContainer>
  <ChatHeader>
    <Avatar user={currentUser} />
    <Title>Chat with {bot.name}</Title>
    <ActionButtons>
      <IconButton icon={<Settings />} />
    </ActionButtons>
  </ChatHeader>
  
  <MessageList>
    <AnimatePresence>
      {messages.map(message => (
        <MessageBubble
          key={message.id}
          message={message}
          isOwn={message.userId === currentUser.id}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      ))}
    </AnimatePresence>
    {isTyping && <TypingIndicator />}
  </MessageList>
  
  <ChatInput
    value={input}
    onChange={setInput}
    onSend={handleSend}
    disabled={isSending}
    placeholder="Type your message..."
  />
</ChatContainer>
```

## Quality Checklist

Before considering ANY component complete:

- [ ] TypeScript types defined (no 'any')
- [ ] Loading state implemented
- [ ] Error state handled
- [ ] Empty state designed
- [ ] Responsive on all screens
- [ ] Keyboard accessible
- [ ] Dark mode supported
- [ ] Animations smooth
- [ ] Form validation working
- [ ] API integration tested

## Color Scheme

Use a professional color palette:

```css
:root {
  --primary: #0F172A;      /* Dark blue-gray */
  --secondary: #3B82F6;    /* Bright blue */
  --accent: #10B981;       /* Green */
  --background: #FFFFFF;
  --surface: #F8FAFC;
  --text: #1E293B;
  --text-muted: #64748B;
  --border: #E2E8F0;
  --error: #EF4444;
  --warning: #F59E0B;
  --success: #10B981;
}

[data-theme='dark'] {
  --primary: #F8FAFC;
  --secondary: #60A5FA;
  --accent: #34D399;
  --background: #0F172A;
  --surface: #1E293B;
  --text: #F1F5F9;
  --text-muted: #94A3B8;
  --border: #334155;
}
```

## Testing Requirements

- Set up Vitest for unit tests
- Test all custom hooks
- Test form validations
- Test API error handling
- Achieve >80% coverage

## Performance Requirements

- Lighthouse score >90
- First Contentful Paint <1.5s
- Time to Interactive <3s
- Implement code splitting
- Lazy load routes
- Optimize images

## Start with These Components First

1. **AppLayout** - Main layout with sidebar
2. **AuthForm** - Login/Register with validation
3. **ChatInterface** - Complete chat UI
4. **BotCard** - Display bot information
5. **SessionList** - Chat session sidebar

Remember: This is an ENTERPRISE application. Every pixel should look professional. Reference apps like Vercel Dashboard, Linear, Notion, or Claude.ai for UI inspiration.

## Using Context7 MCP

If Context7 MCP is available, use it for:
- Component generation
- Layout patterns
- Responsive design
- Accessibility features
- Performance optimization

Ask Context7 for best practices when implementing each feature.