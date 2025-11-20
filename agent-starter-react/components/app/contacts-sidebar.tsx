'use client';

import { useState, useEffect } from 'react';
import { X, Plus, Trash2, Users, Edit2, Check } from 'lucide-react';
import { Button } from '@/components/livekit/button';
import { getAccessToken } from '@/lib/auth';

interface Beneficiary {
  id: string;
  nickname: string;
  fullName: string;
  paymentAddress: string;
  paymentType: 'upi' | 'account';
  bankName?: string | null;
}

interface ContactsSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

export function ContactsSidebar({ isOpen, onToggle }: ContactsSidebarProps) {
  const [contacts, setContacts] = useState<Beneficiary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    nickname: '',
    fullName: '',
    paymentAddress: '',
    paymentType: 'upi' as 'upi' | 'account',
    bankName: '',
  });

  useEffect(() => {
    if (isOpen) {
      fetchContacts();
    }
  }, [isOpen]);

  const fetchContacts = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const token = getAccessToken();
      const response = await fetch('/api/beneficiaries', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch contacts');

      const data = await response.json();
      setContacts(data);
    } catch (err) {
      setError('Failed to load contacts');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddContact = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      const token = getAccessToken();
      const response = await fetch('/api/beneficiaries', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to add contact');
      }

      // Reset form and refresh list
      setFormData({
        nickname: '',
        fullName: '',
        paymentAddress: '',
        paymentType: 'upi',
        bankName: '',
      });
      setIsAdding(false);
      await fetchContacts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add contact');
    }
  };

  const handleUpdateContact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingId) return;
    
    setError(null);

    try {
      const token = getAccessToken();
      const response = await fetch(`/api/beneficiaries/${editingId}`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update contact');
      }

      // Reset form and refresh list
      setFormData({
        nickname: '',
        fullName: '',
        paymentAddress: '',
        paymentType: 'upi',
        bankName: '',
      });
      setEditingId(null);
      await fetchContacts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update contact');
    }
  };

  const handleDeleteContact = async (id: string) => {
    if (!confirm('Are you sure you want to delete this contact?')) return;

    setError(null);
    try {
      const token = getAccessToken();
      const response = await fetch(`/api/beneficiaries/${id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to delete contact');

      await fetchContacts();
    } catch (err) {
      setError('Failed to delete contact');
      console.error(err);
    }
  };

  const startEditing = (contact: Beneficiary) => {
    setEditingId(contact.id);
    setFormData({
      nickname: contact.nickname,
      fullName: contact.fullName,
      paymentAddress: contact.paymentAddress,
      paymentType: contact.paymentType,
      bankName: contact.bankName || '',
    });
    setIsAdding(false);
  };

  const cancelEditing = () => {
    setEditingId(null);
    setFormData({
      nickname: '',
      fullName: '',
      paymentAddress: '',
      paymentType: 'upi',
      bankName: '',
    });
  };

  return (
    <>
      {/* Sidebar */}
      <div
        className={`fixed left-0 top-0 z-40 h-full w-80 transform bg-background shadow-2xl transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col">
          {/* Header with Close Button */}
          <div className="flex items-center justify-between border-b p-4">
            <div className="flex items-center gap-2">
              <Users className="size-5" />
              <div>
                <h2 className="text-xl font-semibold">Contacts</h2>
                <p className="text-muted-foreground text-xs">Manage your payment contacts</p>
              </div>
            </div>
            <button
              onClick={onToggle}
              className="rounded-lg p-2 transition-colors hover:bg-accent"
              aria-label="Close contacts"
            >
              <X className="size-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {error && (
              <div className="mb-4 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-muted-foreground">Loading...</div>
              </div>
            ) : (
              <>
                {/* Contact List */}
                <div className="space-y-2">
                  {contacts.map((contact) => (
                    <div
                      key={contact.id}
                      className="group relative rounded-lg border p-3 transition-colors hover:bg-accent"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="font-medium">{contact.nickname}</h3>
                          <p className="text-muted-foreground text-sm">{contact.fullName}</p>
                          <p className="text-muted-foreground text-xs">{contact.paymentAddress}</p>
                          {contact.bankName && (
                            <p className="text-muted-foreground text-xs">{contact.bankName}</p>
                          )}
                        </div>
                        <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                          <button
                            onClick={() => startEditing(contact)}
                            className="rounded p-1 hover:bg-background"
                            aria-label="Edit contact"
                          >
                            <Edit2 className="size-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteContact(contact.id)}
                            className="rounded p-1 hover:bg-background"
                            aria-label="Delete contact"
                          >
                            <Trash2 className="text-destructive size-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {contacts.length === 0 && !isAdding && !editingId && (
                  <div className="text-muted-foreground py-8 text-center text-sm">
                    No contacts yet. Add one to get started!
                  </div>
                )}
              </>
            )}
          </div>

          {/* Add/Edit Contact Form or Button */}
          <div className="border-t p-4">
            {isAdding || editingId ? (
              <form onSubmit={editingId ? handleUpdateContact : handleAddContact} className="space-y-3">
                <input
                  type="text"
                  placeholder="Nickname (e.g., Mom)"
                  value={formData.nickname}
                  onChange={(e) => setFormData({ ...formData, nickname: e.target.value })}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                  required
                />
                <input
                  type="text"
                  placeholder="Full Name"
                  value={formData.fullName}
                  onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                  required
                />
                <input
                  type="text"
                  placeholder="Payment Address (UPI ID or Account)"
                  value={formData.paymentAddress}
                  onChange={(e) => setFormData({ ...formData, paymentAddress: e.target.value })}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                  required
                />
                <select
                  value={formData.paymentType}
                  onChange={(e) =>
                    setFormData({ ...formData, paymentType: e.target.value as 'upi' | 'account' })
                  }
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                >
                  <option value="upi">UPI</option>
                  <option value="account">Account</option>
                </select>
                <input
                  type="text"
                  placeholder="Bank Name (optional)"
                  value={formData.bankName}
                  onChange={(e) => setFormData({ ...formData, bankName: e.target.value })}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                />
                <div className="flex gap-2">
                  <Button type="submit" className="flex-1" size="sm">
                    {editingId ? (
                      <>
                        <Check className="mr-2 size-4" />
                        Update
                      </>
                    ) : (
                      <>
                        <Plus className="mr-2 size-4" />
                        Add
                      </>
                    )}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={editingId ? cancelEditing : () => setIsAdding(false)}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            ) : (
              <Button onClick={() => setIsAdding(true)} className="w-full" size="sm">
                <Plus className="mr-2 size-4" />
                Add Contact
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/20 backdrop-blur-sm transition-opacity"
          onClick={onToggle}
          aria-hidden="true"
        />
      )}
    </>
  );
}
