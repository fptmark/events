import { HttpInterceptorFn, HttpResponse, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { tap, catchError, switchMap } from 'rxjs/operators';
import { throwError, from } from 'rxjs';
import { AuthService } from '../services/auth.service';

/**
 * HTTP Interceptor for authentication
 *
 * Responsibilities:
 * 1. Add withCredentials to all requests (send cookies)
 * 2. Extract permissions from login response ONLY (client caches for session)
 * 3. Handle 401 Unauthorized - trigger login and retry
 * 4. Handle 403 Forbidden - show error (already authenticated)
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);

  // Add credentials to all requests (send session cookie)
  const authReq = req.clone({
    withCredentials: true
  });

  return next(authReq).pipe(
    // Extract permissions from login response only
    tap(event => {
      if (event instanceof HttpResponse) {
        const body = event.body as any;

        // Only extract session data from login response
        // Both authn and authz are optional services:
        // - No authn: no login endpoint, everything public
        // - Authn without authz: login exists but no permissions, everything permitted
        // - Authn with authz: login with permissions, filter by permissions
        if (req.url.includes('/api/login') && body && body.data) {
          const sessionData = body.data;
          // Extract whatever fields are present - missing permissions means "allow all"
          authService.updateUserSession({
            login: sessionData.login,
            roleId: sessionData.roleId,
            permissions: sessionData.permissions  // May be undefined if authz not configured
          });
          if (sessionData.permissions) {
            console.log('AuthInterceptor: Cached permissions from login:', sessionData.permissions);
          } else {
            console.log('AuthInterceptor: No permissions in login (authz not configured - allow all)');
          }
        }
      }
    }),

    // Handle errors
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401) {
        console.log('AuthInterceptor: 401 Unauthorized - requesting login');

        // Don't trigger login for the /api/login endpoint itself
        if (req.url.includes('/api/login')) {
          return throwError(() => error);
        }

        // Trigger login modal
        authService.requestLogin();

        // Wait for login to complete, then retry original request
        return from(authService.waitForLogin()).pipe(
          switchMap(() => {
            console.log('AuthInterceptor: Login complete, retrying request');
            // Retry the original request with new session
            return next(authReq);
          })
        );
      }

      if (error.status === 403) {
        console.log('AuthInterceptor: 403 Forbidden - access denied');
        // User is authenticated but not authorized
        // Let the error propagate to show via notification service
      }

      return throwError(() => error);
    })
  );
};
