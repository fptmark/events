import { Injectable } from '@angular/core'
import { HttpClient } from '@angular/common/http'
import { Observable, map, of, catchError } from 'rxjs'

interface Config {
  server_url: string
  [key: string]: any
}

@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  // Hard-code the config directly - the simplest approach
  public config: Config = {
    server_url: 'http://localhost:5500',
    // Other config fields would go here
  }

  constructor(private http: HttpClient) {}

  getApiUrl(entityName: string): string {
    return `${this.config.server_url}/api/${entityName.toLowerCase()}`
  }
}