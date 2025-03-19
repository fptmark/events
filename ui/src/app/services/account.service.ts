import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { API_CONFIG } from '../constants';
import { Observable } from 'rxjs';
import { User } from './user.service';

export interface Account {
  id?: string;
  expiredAt?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AccountService {
  private apiUrl = API_CONFIG.getApiUrl('account');

  constructor(private http: HttpClient) {}

  getAccounts(): Observable<Account[]> {
    return this.http.get<Account[]>(this.apiUrl);
  }

  // No create account; accounts are created when a user is an admin.

  deleteAccount(id: string): Observable<any> {
    // Cascade deletion should be handled on the backend.
    return this.http.delete(`${this.apiUrl}/${id}`);
  }

  // Optionally, you could have an endpoint that retrieves account users:
  getUsersByAccount(accountId: string): Observable<User[]> {
    return this.http.get<User[]>(`${this.apiUrl}/${accountId}/users`);
  }
}
