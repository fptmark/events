import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { API_CONFIG } from '../constants';
import { Observable } from 'rxjs';

export interface User {
  id?: string;
  accountId: string;
  username: string;
  email: string;
  password?: string;
  firstName: string;
  lastName: string;
  gender: string;
  isAccountOwner: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class UserService {
  private apiUrl = API_CONFIG.getApiUrl('user');

  constructor(private http: HttpClient) {}

  getUsers(): Observable<User[]> {
    return this.http.get<User[]>(this.apiUrl);
  }

  getUser(id: string): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/${id}`);
  }

  createUser(user: User): Observable<User> {
    return this.http.post<User>(this.apiUrl, user);
  }

  updateUser(id: string, user: User): Observable<User> {
    return this.http.put<User>(`${this.apiUrl}/${id}`, user);
  }

  deleteUser(id: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}`);
  }
}

