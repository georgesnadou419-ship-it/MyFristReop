import request from './request'

export interface BillingSummary {
  total_credits: string;
  used_credits: string;
  remaining: string;
}

export interface BillingRecordItem {
  id: number;
  task_id?: string | null;
  task_name?: string | null;
  resource_type: string;
  gpu_model?: string | null;
  duration_seconds: number;
  duration_display: string;
  cost: string;
  created_at: string
}

export interface BillingRecordsPage {
  items: BillingRecordItem[];
  total: number;
  page: number;
  page_size: number;
}

export async function fetchBillingSummary() {
  return request.get<unknown, BillingSummary>('/billing/summary')
}

export async function fetchBillingRecords(page = 1, pageSize = 20) {
  return request.get<unknown, BillingRecordsPage>('/billing/records', {
    params: { page, page_size: pageSize },
  })
}
