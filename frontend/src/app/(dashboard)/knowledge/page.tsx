'use client';

import { useEffect, useState } from 'react';
import {
  BookOpen,
  Search,
  Plus,
  Edit2,
  Trash2,
  ChevronDown,
  ChevronRight,
  MessageCircle,
  X,
  Save,
} from 'lucide-react';
import { KnowledgeEntry, BusinessInfo } from '@/lib/types';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface KnowledgeData {
  business_info: BusinessInfo;
  faqs: KnowledgeEntry[];
}

interface EntryFormData {
  category: string;
  question: string;
  answer: string;
  keywords: string;
}

export default function KnowledgePage() {
  const [knowledgeData, setKnowledgeData] = useState<KnowledgeData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  
  // Modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingEntry, setEditingEntry] = useState<KnowledgeEntry | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState<EntryFormData>({
    category: '',
    question: '',
    answer: '',
    keywords: '',
  });

  useEffect(() => {
    async function loadKnowledge() {
      try {
        setIsLoading(true);
        const data = await api.getKnowledgeBase();
        setKnowledgeData(data);
        // Expand all categories by default
        const categories = new Set(data.faqs.map((faq) => faq.category));
        setExpandedCategories(categories);
      } catch (err) {
        console.error('Failed to load knowledge base:', err);
        // Fallback data
        setKnowledgeData({
          business_info: {
            name: 'Mash Voice',
            tagline: 'AI-Powered Customer Service',
            tone: 'professional',
            timezone: 'America/New_York',
          },
          faqs: [],
        });
      } finally {
        setIsLoading(false);
      }
    }

    loadKnowledge();
  }, []);

  const handleOpenAddModal = () => {
    setFormData({
      category: '',
      question: '',
      answer: '',
      keywords: '',
    });
    setShowAddModal(true);
  };

  const handleOpenEditModal = (entry: KnowledgeEntry) => {
    setEditingEntry(entry);
    setFormData({
      category: entry.category,
      question: entry.question,
      answer: entry.answer,
      keywords: entry.keywords.join(', '),
    });
    setShowEditModal(true);
  };

  const handleCloseModal = () => {
    setShowAddModal(false);
    setShowEditModal(false);
    setEditingEntry(null);
    setFormData({
      category: '',
      question: '',
      answer: '',
      keywords: '',
    });
  };

  const handleAddEntry = async () => {
    if (!formData.question.trim() || !formData.answer.trim()) {
      alert('Question and answer are required');
      return;
    }

    try {
      setIsSaving(true);
      const newEntry = await api.addKnowledgeEntry({
        category: formData.category.trim() || 'General',
        question: formData.question.trim(),
        answer: formData.answer.trim(),
        keywords: formData.keywords
          .split(',')
          .map((k) => k.trim())
          .filter((k) => k.length > 0),
      });

      // Update local state
      setKnowledgeData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          faqs: [...prev.faqs, newEntry],
        };
      });

      // Expand the category
      setExpandedCategories((prev) => new Set(prev).add(newEntry.category));

      handleCloseModal();
    } catch (err) {
      console.error('Failed to add entry:', err);
      alert('Failed to add entry. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateEntry = async () => {
    if (!editingEntry || !formData.question.trim() || !formData.answer.trim()) {
      alert('Question and answer are required');
      return;
    }

    try {
      setIsSaving(true);
      const updatedEntry = await api.updateKnowledgeEntry(editingEntry.id, {
        category: formData.category.trim() || 'General',
        question: formData.question.trim(),
        answer: formData.answer.trim(),
        keywords: formData.keywords
          .split(',')
          .map((k) => k.trim())
          .filter((k) => k.length > 0),
      });

      // Update local state
      setKnowledgeData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          faqs: prev.faqs.map((faq) =>
            faq.id === editingEntry.id ? updatedEntry : faq
          ),
        };
      });

      handleCloseModal();
    } catch (err) {
      console.error('Failed to update entry:', err);
      alert('Failed to update entry. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteEntry = async (id: string) => {
    if (!confirm('Are you sure you want to delete this entry?')) return;

    try {
      await api.deleteKnowledgeEntry(id);

      // Update local state
      setKnowledgeData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          faqs: prev.faqs.filter((faq) => faq.id !== id),
        };
      });
    } catch (err) {
      console.error('Failed to delete entry:', err);
      alert('Failed to delete entry. Please try again.');
    }
  };

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  const filteredFaqs = knowledgeData?.faqs.filter((faq) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      faq.question.toLowerCase().includes(query) ||
      faq.answer.toLowerCase().includes(query) ||
      faq.keywords.some((k) => k.toLowerCase().includes(query))
    );
  }) || [];

  const groupedFaqs = filteredFaqs.reduce((acc, faq) => {
    if (!acc[faq.category]) {
      acc[faq.category] = [];
    }
    acc[faq.category].push(faq);
    return acc;
  }, {} as Record<string, KnowledgeEntry[]>);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Knowledge Base</h1>
          <p className="text-muted-foreground mt-1">
            Manage FAQs and business information for AI responses
          </p>
        </div>
        <button
          onClick={handleOpenAddModal}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg',
            'bg-primary text-primary-foreground',
            'hover:bg-primary/90 transition-colors'
          )}
        >
          <Plus className="w-4 h-4" />
          Add Entry
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* FAQs List */}
          <div className="lg:col-span-2 space-y-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search knowledge base..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={cn(
                  'w-full pl-10 pr-4 py-2.5 rounded-lg text-sm',
                  'bg-background border border-input',
                  'placeholder:text-muted-foreground',
                  'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                )}
              />
            </div>

            {/* Categories */}
            {Object.entries(groupedFaqs).length === 0 ? (
              <div className="bg-card border border-border rounded-xl p-12 text-center">
                <BookOpen className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="font-semibold text-foreground mb-2">No entries found</h3>
                <p className="text-sm text-muted-foreground">
                  {searchQuery
                    ? 'Try a different search term'
                    : 'Add your first knowledge base entry'}
                </p>
              </div>
            ) : (
              Object.entries(groupedFaqs).map(([category, faqs]) => (
                <div
                  key={category}
                  className="bg-card border border-border rounded-xl overflow-hidden"
                >
                  <button
                    onClick={() => toggleCategory(category)}
                    className="w-full flex items-center justify-between px-4 py-3 bg-accent/50 hover:bg-accent transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      {expandedCategories.has(category) ? (
                        <ChevronDown className="w-4 h-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                      )}
                      <span className="font-medium text-foreground">{category}</span>
                      <span className="text-xs text-muted-foreground bg-background px-2 py-0.5 rounded-full">
                        {faqs.length}
                      </span>
                    </div>
                  </button>

                  {expandedCategories.has(category) && (
                    <div className="divide-y divide-border">
                      {faqs.map((faq) => (
                        <div key={faq.id} className="p-4 hover:bg-accent/30 transition-colors">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <MessageCircle className="w-4 h-4 text-primary mt-0.5" />
                                <div>
                                  <h4 className="font-medium text-foreground">
                                    {faq.question}
                                  </h4>
                                  <p className="text-sm text-muted-foreground mt-1">
                                    {faq.answer}
                                  </p>
                                  <div className="flex flex-wrap gap-1 mt-2">
                                    {faq.keywords.map((keyword) => (
                                      <span
                                        key={keyword}
                                        className="text-xs bg-accent px-2 py-0.5 rounded"
                                      >
                                        {keyword}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => handleOpenEditModal(faq)}
                                className="p-1.5 rounded hover:bg-accent transition-colors"
                                title="Edit entry"
                              >
                                <Edit2 className="w-4 h-4 text-muted-foreground" />
                              </button>
                              <button
                                onClick={() => handleDeleteEntry(faq.id)}
                                className="p-1.5 rounded hover:bg-accent transition-colors"
                                title="Delete entry"
                              >
                                <Trash2 className="w-4 h-4 text-muted-foreground hover:text-red-500" />
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Business Info Panel */}
          <div className="lg:col-span-1">
            <div className="bg-card border border-border rounded-xl p-5 sticky top-6">
              <h3 className="font-semibold text-foreground mb-4">Business Information</h3>
              
              {knowledgeData?.business_info && (
                <div className="space-y-4">
                  <div>
                    <label className="text-xs text-muted-foreground uppercase tracking-wider">
                      Name
                    </label>
                    <p className="text-sm font-medium text-foreground mt-1">
                      {knowledgeData.business_info.name}
                    </p>
                  </div>
                  
                  {knowledgeData.business_info.tagline && (
                    <div>
                      <label className="text-xs text-muted-foreground uppercase tracking-wider">
                        Tagline
                      </label>
                      <p className="text-sm font-medium text-foreground mt-1">
                        {knowledgeData.business_info.tagline}
                      </p>
                    </div>
                  )}
                  
                  {knowledgeData.business_info.tone && (
                    <div>
                      <label className="text-xs text-muted-foreground uppercase tracking-wider">
                        Communication Tone
                      </label>
                      <p className="text-sm font-medium text-foreground mt-1 capitalize">
                        {knowledgeData.business_info.tone}
                      </p>
                    </div>
                  )}
                  
                  {knowledgeData.business_info.timezone && (
                    <div>
                      <label className="text-xs text-muted-foreground uppercase tracking-wider">
                        Timezone
                      </label>
                      <p className="text-sm font-medium text-foreground mt-1">
                        {knowledgeData.business_info.timezone}
                      </p>
                    </div>
                  )}

                  {knowledgeData.business_info.contact && (
                    <div className="border-t border-border pt-4">
                      <label className="text-xs text-muted-foreground uppercase tracking-wider">
                        Contact Information
                      </label>
                      <div className="mt-2 space-y-1">
                        {knowledgeData.business_info.contact.email && (
                          <p className="text-sm text-foreground">
                            {knowledgeData.business_info.contact.email}
                          </p>
                        )}
                        {knowledgeData.business_info.contact.phone && (
                          <p className="text-sm text-foreground">
                            {knowledgeData.business_info.contact.phone}
                          </p>
                        )}
                        {knowledgeData.business_info.contact.website && (
                          <p className="text-sm text-foreground">
                            {knowledgeData.business_info.contact.website}
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <button
                className={cn(
                  'w-full mt-4 flex items-center justify-center gap-2 px-4 py-2 rounded-lg',
                  'border border-border text-muted-foreground',
                  'hover:bg-accent transition-colors'
                )}
              >
                <Edit2 className="w-4 h-4" />
                Edit Business Info
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add/Edit Entry Modal */}
      {(showAddModal || showEditModal) && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-border">
              <h2 className="text-xl font-semibold text-foreground">
                {showEditModal ? 'Edit Knowledge Entry' : 'Add Knowledge Entry'}
              </h2>
              <button
                onClick={handleCloseModal}
                className="p-2 rounded-lg hover:bg-accent transition-colors"
              >
                <X className="w-5 h-5 text-muted-foreground" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4">
              {/* Category */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Category
                </label>
                <input
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  placeholder="e.g., General, Technical, Billing"
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg text-sm',
                    'bg-background border border-input',
                    'placeholder:text-muted-foreground',
                    'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                  )}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Leave empty for "General" category
                </p>
              </div>

              {/* Question */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Question <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.question}
                  onChange={(e) => setFormData({ ...formData, question: e.target.value })}
                  placeholder="What question does this answer?"
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg text-sm',
                    'bg-background border border-input',
                    'placeholder:text-muted-foreground',
                    'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                  )}
                />
              </div>

              {/* Answer */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Answer <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={formData.answer}
                  onChange={(e) => setFormData({ ...formData, answer: e.target.value })}
                  placeholder="Provide a detailed answer that the AI will use..."
                  rows={6}
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg text-sm',
                    'bg-background border border-input',
                    'placeholder:text-muted-foreground',
                    'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary',
                    'resize-none'
                  )}
                />
              </div>

              {/* Keywords */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Keywords
                </label>
                <input
                  type="text"
                  value={formData.keywords}
                  onChange={(e) => setFormData({ ...formData, keywords: e.target.value })}
                  placeholder="e.g., pricing, cost, payment, subscription"
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg text-sm',
                    'bg-background border border-input',
                    'placeholder:text-muted-foreground',
                    'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                  )}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Comma-separated keywords to help match user questions
                </p>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 p-6 border-t border-border">
              <button
                onClick={handleCloseModal}
                disabled={isSaving}
                className={cn(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  'border border-border text-muted-foreground hover:bg-accent',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                Cancel
              </button>
              <button
                onClick={showEditModal ? handleUpdateEntry : handleAddEntry}
                disabled={isSaving || !formData.question.trim() || !formData.answer.trim()}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  'bg-primary text-primary-foreground hover:bg-primary/90',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                {isSaving ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    {showEditModal ? 'Update Entry' : 'Add Entry'}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
