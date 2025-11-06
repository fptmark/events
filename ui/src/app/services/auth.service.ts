import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Subject, firstValueFrom } from 'rxjs';
import { ConfigService } from './config.service';
import { ServiceMetadata } from './metadata.service';

export interface UserSession {
  login: string;
  roleId?: string;
  permissions?: any;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private authnConfig$ = new BehaviorSubject<ServiceMetadata | null>(null);
  private permissions$ = new BehaviorSubject<any>(null);
  private userSession$ = new BehaviorSubject<UserSession | null>(null);
  private showLoginModal$ = new Subject<void>();
  private loginComplete$ = new Subject<void>();

  // Observable streams for components
  authnConfig = this.authnConfig$.asObservable();
  permissions = this.permissions$.asObservable();
  userSession = this.userSession$.asObservable();
  showLoginModal = this.showLoginModal$.asObservable();

  constructor(
    private http: HttpClient,
    private configService: ConfigService
  ) {}

  /**
   * Set the authn service configuration from metadata
   */
  setAuthnConfig(config: ServiceMetadata | null): void {
    this.authnConfig$.next(config);
    console.log('AuthService: Authn config set:', config);
  }

  /**
   * Get current authn configuration
   */
  getAuthnConfig(): ServiceMetadata | null {
    return this.authnConfig$.value;
  }

  /**
   * Update permissions from server response
   */
  updatePermissions(permissions: any): void {
    if (permissions) {
      this.permissions$.next(permissions);
      console.log('AuthService: Permissions updated:', permissions);
    }
  }

  /**
   * Update user session data from server response
   */
  updateUserSession(session: UserSession): void {
    this.userSession$.next(session);
    this.updatePermissions(session.permissions);
    console.log('AuthService: User session updated:', session);
  }

  /**
   * Get current permissions
   */
  getPermissions(): any {
    return this.permissions$.value;
  }

  /**
   * Get current user session
   */
  getUserSession(): UserSession | null {
    return this.userSession$.value;
  }

  /**
   * Check if user has permission for entity operation
   * @param entity Entity name (e.g., "User")
   * @param operation Operation character (e.g., "c", "r", "u", "d")
   */
  hasPermission(entity: string, operation: string): boolean {
    const perms = this.permissions$.value;
    if (!perms) return false;

    // Check wildcard first - applies to all entities
    if (perms['*']) {
      const wildcardPerms = perms['*'];
      if (wildcardPerms && wildcardPerms !== '') {
        return wildcardPerms.includes(operation);
      }
    }

    // Case-insensitive entity lookup
    const entityKey = Object.keys(perms).find(
      key => key.toLowerCase() === entity.toLowerCase()
    );

    if (!entityKey) return false;
    const entityPerms = perms[entityKey];

    // Empty string means no permissions
    if (!entityPerms || entityPerms === '') return false;

    return entityPerms.includes(operation);
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.userSession$.value !== null;
  }

  /**
   * Trigger login modal to appear
   */
  requestLogin(): void {
    console.log('AuthService: Login requested (401 detected)');
    this.showLoginModal$.next();
  }

  /**
   * Wait for login to complete
   * Used by interceptor to queue requests during login
   */
  async waitForLogin(): Promise<void> {
    return new Promise((resolve) => {
      const subscription = this.loginComplete$.subscribe(() => {
        subscription.unsubscribe();
        resolve();
      });
    });
  }

  /**
   * Perform login
   */
  async login(credentials: any): Promise<UserSession> {
    const url = this.configService.getApiUrl('login');

    try {
      const response = await firstValueFrom(
        this.http.post<any>(url, credentials, { withCredentials: true })
      );

      // Extract user session from response
      const session: UserSession = {
        login: credentials[Object.keys(credentials)[0]], // First input field value
        roleId: response.data?.roleId || response.roleId,
        permissions: response.permissions
      };

      this.updateUserSession(session);
      this.loginComplete$.next();

      console.log('AuthService: Login successful');
      return session;

    } catch (error: any) {
      console.error('AuthService: Login failed:', error);
      throw error;
    }
  }

  /**
   * Perform logout
   */
  async logout(): Promise<void> {
    const url = this.configService.getApiUrl('logout');

    try {
      await firstValueFrom(
        this.http.post(url, {}, { withCredentials: true })
      );

      // Clear local state
      this.userSession$.next(null);
      this.permissions$.next(null);

      console.log('AuthService: Logout successful');

      // Show login modal
      this.requestLogin();

    } catch (error) {
      console.error('AuthService: Logout failed:', error);
      throw error;
    }
  }
}
