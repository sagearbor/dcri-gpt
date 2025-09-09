import React, { useEffect } from 'react';
import { Plus, MessageSquare, Trash2, Clock } from 'lucide-react';
import { useChatStore } from '@/stores/chatStore';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ChatSession } from '@/types';

const SessionItem: React.FC<{
  session: ChatSession;
  isActive: boolean;
  onSelect: () => void;
  onDelete?: () => void;
}> = ({ session, isActive, onSelect, onDelete }) => {
  const formatDate = (date: string) => {
    const d = new Date(date);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (days === 1) {
      return 'Yesterday';
    } else if (days < 7) {
      return d.toLocaleDateString([], { weekday: 'short' });
    } else {
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  return (
    <div
      className={cn(
        'group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors',
        isActive 
          ? 'bg-secondary text-secondary-foreground' 
          : 'hover:bg-gray-100 dark:hover:bg-gray-800'
      )}
      onClick={onSelect}
    >
      <MessageSquare className="w-4 h-4 flex-shrink-0" />
      
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">
          {session.title || 'New Chat'}
        </p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Clock className="w-3 h-3" />
          <span>{formatDate(session.updated_at)}</span>
          {session.message_count > 0 && (
            <>
              <span>•</span>
              <span>{session.message_count} messages</span>
            </>
          )}
        </div>
      </div>
      
      {onDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-opacity"
        >
          <Trash2 className="w-3 h-3 text-red-500" />
        </button>
      )}
    </div>
  );
};

export const SessionList: React.FC = () => {
  const { 
    sessions, 
    currentSession, 
    fetchSessions, 
    createSession, 
    selectSession,
    isLoading 
  } = useChatStore();

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleNewSession = async () => {
    try {
      const session = await createSession();
      await selectSession(session.id);
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    // TODO: Implement delete session
    console.log('Delete session:', sessionId);
  };

  // Group sessions by date
  const groupedSessions = React.useMemo(() => {
    const groups: Record<string, ChatSession[]> = {
      today: [],
      yesterday: [],
      thisWeek: [],
      older: [],
    };

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 7);

    sessions.forEach(session => {
      const sessionDate = new Date(session.updated_at);
      
      if (sessionDate >= today) {
        groups.today.push(session);
      } else if (sessionDate >= yesterday) {
        groups.yesterday.push(session);
      } else if (sessionDate >= weekAgo) {
        groups.thisWeek.push(session);
      } else {
        groups.older.push(session);
      }
    });

    return groups;
  }, [sessions]);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4">
        <Button onClick={handleNewSession} className="w-full" variant="outline">
          <Plus className="w-4 h-4 mr-2" />
          New Chat
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 scrollbar-thin">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-8">
            <MessageSquare className="w-8 h-8 text-gray-400 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">No conversations yet</p>
          </div>
        ) : (
          <div className="space-y-4">
            {groupedSessions.today.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-muted-foreground px-3 mb-1">
                  TODAY
                </h3>
                <div className="space-y-1">
                  {groupedSessions.today.map(session => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      isActive={currentSession?.id === session.id}
                      onSelect={() => selectSession(session.id)}
                      onDelete={() => handleDeleteSession(session.id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {groupedSessions.yesterday.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-muted-foreground px-3 mb-1">
                  YESTERDAY
                </h3>
                <div className="space-y-1">
                  {groupedSessions.yesterday.map(session => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      isActive={currentSession?.id === session.id}
                      onSelect={() => selectSession(session.id)}
                      onDelete={() => handleDeleteSession(session.id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {groupedSessions.thisWeek.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-muted-foreground px-3 mb-1">
                  THIS WEEK
                </h3>
                <div className="space-y-1">
                  {groupedSessions.thisWeek.map(session => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      isActive={currentSession?.id === session.id}
                      onSelect={() => selectSession(session.id)}
                      onDelete={() => handleDeleteSession(session.id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {groupedSessions.older.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-muted-foreground px-3 mb-1">
                  OLDER
                </h3>
                <div className="space-y-1">
                  {groupedSessions.older.map(session => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      isActive={currentSession?.id === session.id}
                      onSelect={() => selectSession(session.id)}
                      onDelete={() => handleDeleteSession(session.id)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};