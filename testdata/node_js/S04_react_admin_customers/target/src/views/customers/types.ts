export enum CustomerStatus {
  Prospect = 'prospect',
  InProgress = 'in_progress',
  Active = 'active',
  Churned = 'churned',
}

export enum CustomerSource {
  Website = 'website',
  Referral = 'referral',
  Ads = 'ads',
  Partner = 'partner',
  Other = 'other',
}

export interface Customer {
  id: string
  name: string
  email: string
  phone?: string
  company?: string
  position?: string
  source: CustomerSource
  status: CustomerStatus
  owner?: string
  lifetimeValue?: number
  monthlyRecurringRevenue?: number
  notes?: string
  createdAt: string
  updatedAt?: string
}

export interface CustomerActivity {
  id: string
  customerId: string
  actor: string
  type: 'note' | 'call' | 'email' | 'deal'
  summary: string
  timestamp: string
  statusAfter?: CustomerStatus
}

export interface CustomerFilters {
  keyword?: string
  status?: CustomerStatus[]
  source?: CustomerSource[]
  owner?: string
  dateRange?: [string, string]
}

export interface CustomerFormValues {
  name: string
  email: string
  phone?: string
  company?: string
  position?: string
  source: CustomerSource
  status: CustomerStatus
  owner?: string
  notes?: string
}

