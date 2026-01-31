'use client';

import { useEffect, useState } from 'react';
import {
  Settings,
  Key,
  Bell,
  Shield,
  Database,
  MessageSquare,
  Save,
  Eye,
  EyeOff,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import { HealthStatus } from '@/lib/types';

interface SettingsSection {
  id: string;
  title: string;
  icon: React.ElementType;
}

const sections: SettingsSection[] = [
  { id: 'api', title: 'API Keys', icon: Key },
  { id: 'whatsapp', title: 'WhatsApp', icon: MessageSquare },
  { id: 'notifications', title: 'Notifications', icon: Bell },
  { id: 'security', title: 'Security', icon: Shield },
  { id: 'database', title: 'Database', icon: Database },
];

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState('api');
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    async function checkHealth() {
      try {
        const data = await api.getHealth();
        setHealth(data);
      } catch (err) {
        setHealth({
          status: 'unhealthy',
          version: 'unknown',
          services: {},
        });
      }
    }
    checkHealth();
  }, []);

  const toggleKeyVisibility = (key: string) => {
    setShowKeys((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    // Simulate save
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Configure your Mash Voice platform
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar Navigation */}
        <div className="lg:col-span-1">
          <nav className="space-y-1">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={cn(
                  'w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors',
                  activeSection === section.id
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                )}
              >
                <section.icon className="w-5 h-5" />
                {section.title}
              </button>
            ))}
          </nav>

          {/* System Status */}
          <div className="mt-6 p-4 bg-card border border-border rounded-xl">
            <h3 className="text-sm font-medium text-foreground mb-3">System Status</h3>
            <div className="flex items-center gap-2">
              {health?.status === 'healthy' ? (
                <>
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  <span className="text-sm text-green-600 dark:text-green-400">
                    All systems operational
                  </span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-4 h-4 text-amber-500" />
                  <span className="text-sm text-amber-600 dark:text-amber-400">
                    Some services unavailable
                  </span>
                </>
              )}
            </div>
            {health?.version && (
              <p className="text-xs text-muted-foreground mt-2">
                Version: {health.version}
              </p>
            )}
          </div>
        </div>

        {/* Settings Content */}
        <div className="lg:col-span-3">
          {/* API Keys Section */}
          {activeSection === 'api' && (
            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="text-lg font-semibold text-foreground mb-4">API Keys</h2>
              <p className="text-sm text-muted-foreground mb-6">
                Configure your external service API keys. These are stored securely and used for AI and messaging services.
              </p>

              <div className="space-y-4">
                {/* Gemini API Key */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Google Gemini API Key
                  </label>
                  <div className="relative">
                    <input
                      type={showKeys['gemini'] ? 'text' : 'password'}
                      placeholder="AIza..."
                      className={cn(
                        'w-full px-4 py-2.5 pr-12 rounded-lg text-sm',
                        'bg-background border border-input',
                        'placeholder:text-muted-foreground',
                        'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                      )}
                    />
                    <button
                      onClick={() => toggleKeyVisibility('gemini')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showKeys['gemini'] ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Used for AI chat completions with Gemini 2.0 Flash
                  </p>
                </div>

                {/* Deepgram API Key */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Deepgram API Key
                  </label>
                  <div className="relative">
                    <input
                      type={showKeys['deepgram'] ? 'text' : 'password'}
                      placeholder="Enter Deepgram API key..."
                      className={cn(
                        'w-full px-4 py-2.5 pr-12 rounded-lg text-sm',
                        'bg-background border border-input',
                        'placeholder:text-muted-foreground',
                        'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                      )}
                    />
                    <button
                      onClick={() => toggleKeyVisibility('deepgram')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showKeys['deepgram'] ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Used for voice message transcription (ASR)
                  </p>
                </div>

                {/* ElevenLabs API Key */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    ElevenLabs API Key (Optional)
                  </label>
                  <div className="relative">
                    <input
                      type={showKeys['elevenlabs'] ? 'text' : 'password'}
                      placeholder="Enter ElevenLabs API key..."
                      className={cn(
                        'w-full px-4 py-2.5 pr-12 rounded-lg text-sm',
                        'bg-background border border-input',
                        'placeholder:text-muted-foreground',
                        'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                      )}
                    />
                    <button
                      onClick={() => toggleKeyVisibility('elevenlabs')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showKeys['elevenlabs'] ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Used for text-to-speech voice responses (TTS)
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* WhatsApp Section */}
          {activeSection === 'whatsapp' && (
            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="text-lg font-semibold text-foreground mb-4">WhatsApp Configuration</h2>
              <p className="text-sm text-muted-foreground mb-6">
                Configure your WhatsApp Business API credentials for messaging.
              </p>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Access Token
                  </label>
                  <div className="relative">
                    <input
                      type={showKeys['whatsapp_token'] ? 'text' : 'password'}
                      placeholder="EAAx..."
                      className={cn(
                        'w-full px-4 py-2.5 pr-12 rounded-lg text-sm',
                        'bg-background border border-input',
                        'placeholder:text-muted-foreground',
                        'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                      )}
                    />
                    <button
                      onClick={() => toggleKeyVisibility('whatsapp_token')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showKeys['whatsapp_token'] ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Phone Number ID
                  </label>
                  <input
                    type="text"
                    placeholder="123456789012345"
                    className={cn(
                      'w-full px-4 py-2.5 rounded-lg text-sm',
                      'bg-background border border-input',
                      'placeholder:text-muted-foreground',
                      'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                    )}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Webhook Verify Token
                  </label>
                  <input
                    type="text"
                    placeholder="your-verify-token"
                    className={cn(
                      'w-full px-4 py-2.5 rounded-lg text-sm',
                      'bg-background border border-input',
                      'placeholder:text-muted-foreground',
                      'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                    )}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Used for webhook verification with Meta
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Notifications Section */}
          {activeSection === 'notifications' && (
            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="text-lg font-semibold text-foreground mb-4">Notification Settings</h2>
              <p className="text-sm text-muted-foreground mb-6">
                Configure how and when you receive notifications.
              </p>

              <div className="space-y-4">
                <div className="flex items-center justify-between py-3 border-b border-border">
                  <div>
                    <p className="text-sm font-medium text-foreground">New Conversations</p>
                    <p className="text-xs text-muted-foreground">Get notified when a new conversation starts</p>
                  </div>
                  <button className="w-11 h-6 bg-primary rounded-full relative">
                    <span className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full" />
                  </button>
                </div>

                <div className="flex items-center justify-between py-3 border-b border-border">
                  <div>
                    <p className="text-sm font-medium text-foreground">Escalations</p>
                    <p className="text-xs text-muted-foreground">Get notified when a conversation is escalated</p>
                  </div>
                  <button className="w-11 h-6 bg-primary rounded-full relative">
                    <span className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full" />
                  </button>
                </div>

                <div className="flex items-center justify-between py-3 border-b border-border">
                  <div>
                    <p className="text-sm font-medium text-foreground">Daily Summary</p>
                    <p className="text-xs text-muted-foreground">Receive a daily summary of activity</p>
                  </div>
                  <button className="w-11 h-6 bg-muted rounded-full relative">
                    <span className="absolute left-1 top-1 w-4 h-4 bg-muted-foreground rounded-full" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Security Section */}
          {activeSection === 'security' && (
            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="text-lg font-semibold text-foreground mb-4">Security Settings</h2>
              <p className="text-sm text-muted-foreground mb-6">
                Manage security and access controls.
              </p>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    JWT Secret Key
                  </label>
                  <div className="relative">
                    <input
                      type={showKeys['jwt'] ? 'text' : 'password'}
                      placeholder="Enter JWT secret..."
                      className={cn(
                        'w-full px-4 py-2.5 pr-12 rounded-lg text-sm',
                        'bg-background border border-input',
                        'placeholder:text-muted-foreground',
                        'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                      )}
                    />
                    <button
                      onClick={() => toggleKeyVisibility('jwt')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showKeys['jwt'] ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between py-3 border-t border-border">
                  <div>
                    <p className="text-sm font-medium text-foreground">API Rate Limiting</p>
                    <p className="text-xs text-muted-foreground">Limit API requests per minute</p>
                  </div>
                  <input
                    type="number"
                    defaultValue={100}
                    className={cn(
                      'w-24 px-3 py-1.5 rounded-lg text-sm text-right',
                      'bg-background border border-input',
                      'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                    )}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Database Section */}
          {activeSection === 'database' && (
            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="text-lg font-semibold text-foreground mb-4">Database Configuration</h2>
              <p className="text-sm text-muted-foreground mb-6">
                Configure database and cache connections.
              </p>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    PostgreSQL URL
                  </label>
                  <div className="relative">
                    <input
                      type={showKeys['postgres'] ? 'text' : 'password'}
                      placeholder="postgresql://user:pass@localhost:5432/dbname"
                      className={cn(
                        'w-full px-4 py-2.5 pr-12 rounded-lg text-sm',
                        'bg-background border border-input',
                        'placeholder:text-muted-foreground',
                        'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                      )}
                    />
                    <button
                      onClick={() => toggleKeyVisibility('postgres')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showKeys['postgres'] ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Redis URL
                  </label>
                  <div className="relative">
                    <input
                      type={showKeys['redis'] ? 'text' : 'password'}
                      placeholder="redis://localhost:6379"
                      className={cn(
                        'w-full px-4 py-2.5 pr-12 rounded-lg text-sm',
                        'bg-background border border-input',
                        'placeholder:text-muted-foreground',
                        'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                      )}
                    />
                    <button
                      onClick={() => toggleKeyVisibility('redis')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showKeys['redis'] ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Save Button */}
          <div className="flex justify-end mt-6">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className={cn(
                'flex items-center gap-2 px-6 py-2.5 rounded-lg font-medium',
                'bg-primary text-primary-foreground',
                'hover:bg-primary/90 transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              <Save className="w-4 h-4" />
              {isSaving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
