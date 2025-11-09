import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Subject, firstValueFrom } from 'rxjs';
import { ConfigService } from './config.service';
import { ServiceMetadata } from './metadata.service';

export interface ExpandedPermissions {
  entity: { [key: string]: string }; // Entity -> operations map (e.g., {"User": "cru"})
  reports: any[];                    // Future: navbar reports with location
}

export interface UserSession {
  login: string;
  roleId?: string;
  permissions?: ExpandedPermissions;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private authnConfigs: ServiceMetadata[] = [];  // All authn configs
  private currentConfigIndex = 0;                 // Current selected config
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
   * Set all authn service configurations from metadata
   * Configs should be sorted with default first
   */
  setAuthnConfigs(configs: ServiceMetadata[]): void {
    this.authnConfigs = configs;
    this.currentConfigIndex = 0;
    this.authnConfig$.next(configs.length > 0 ? configs[0] : null);
    console.log('AuthService: Authn configs set:', configs);
  }

  /**
   * Set the authn service configuration from metadata (backwards compatible)
   */
  setAuthnConfig(config: ServiceMetadata | null): void {
    this.authnConfigs = config ? [config] : [];
    this.currentConfigIndex = 0;
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
   * Check if there are multiple authn configs
   */
  hasMultipleAuthnConfigs(): boolean {
    return this.authnConfigs.length > 1;
  }

  /**
   * Rotate to next authn configuration
   * Cycles through all available configs
   */
  rotateAuthnConfig(): void {
    if (this.authnConfigs.length <= 1) {
      return; // Nothing to rotate
    }

    this.currentConfigIndex = (this.currentConfigIndex + 1) % this.authnConfigs.length;
    const newConfig = this.authnConfigs[this.currentConfigIndex];
    this.authnConfig$.next(newConfig);
    console.log('AuthService: Rotated to config:', newConfig.label || newConfig.route);
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
   * Check if entity should appear in dashboard
   * @param entity Entity name (e.g., "User")
   * @returns true if entity has permissions or if authz not configured (allow all)
   */
  isEntityOnDashboard(entity: string): boolean {
    const perms = this.permissions$.value;

    // No permissions object = authz not configured = allow all
    if (!perms) return true;

    // No entity map = malformed permissions = deny
    if (!perms.entity) return false;

    // Case-insensitive lookup in entity keys (dashboard is derived from entity map)
    const entityKeys = Object.keys(perms.entity);
    return entityKeys.some(
      (key: string) => key.toLowerCase() === entity.toLowerCase()
    );
  }

  /**
   * Check if user has permission for entity operation
   * @param entity Entity name (e.g., "User")
   * @param operation Operation character (e.g., "c", "r", "u", "d")
   * @returns true if operation permitted or if authz not configured (allow all)
   */
  hasPermission(entity: string, operation: string): boolean {
    const perms = this.permissions$.value;

    // No permissions object = authz not configured = allow all
    if (!perms) return true;

    // No entity map = malformed permissions = deny
    if (!perms.entity) return false;

    // Case-insensitive entity lookup in entity map
    const entityKey = Object.keys(perms.entity).find(
      key => key.toLowerCase() === entity.toLowerCase()
    );

    if (!entityKey) return false;
    const entityPerms = perms.entity[entityKey];

    // Empty string means no permissions for this entity
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
    const config = this.getAuthnConfig();
    if (!config || !config.route) {
      throw new Error('No authn configuration available');
    }
    const url = this.configService.getApiUrl(config.route);

    try {
      const response = await firstValueFrom(
        this.http.post<any>(url, credentials, { withCredentials: true })
      );

      // Extract user session from response
      // Permissions are in response.data.permissions (expanded format from server)
      const session: UserSession = {
        login: credentials[Object.keys(credentials)[0]], // First input field value
        roleId: response.data?.roleId || response.roleId,
        permissions: response.data?.permissions
      };

      this.updateUserSession(session);
      this.loginComplete$.next();

      console.log('AuthService: Login successful, permissions:', session.permissions);
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

  /**
   * Fetch current session from server
   * Used on page refresh to restore permissions without re-login
   */
  async fetchSession(): Promise<UserSession | null> {
    const url = this.configService.getApiUrl('session');

    try {
      const response = await firstValueFrom(
        this.http.get<any>(url, { withCredentials: true })
      );

      // Extract user session from response
      const session: UserSession = {
        login: response.data?.login || response.login,
        roleId: response.data?.roleId || response.roleId,
        permissions: response.data?.permissions || response.permissions
      };

      this.updateUserSession(session);

      console.log('AuthService: Session fetched successfully, permissions:', session.permissions);
      return session;

    } catch (error: any) {
      // 401 = no valid session, trigger login
      if (error.status === 401) {
        console.log('AuthService: No valid session, requesting login');
        this.requestLogin();
        return null;
      }
      console.error('AuthService: Session fetch failed:', error);
      throw error;
    }
  }
}
