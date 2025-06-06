import { TestBed } from '@angular/core/testing';
import { AppComponent } from './app.component';
import { MetadataService } from './services/metadata.service';
import { NavigationService } from './services/navigation.service';
import { ConfigService } from './services/config.service';
import { RestService } from './services/rest.service';
import { of } from 'rxjs';

describe('AppComponent', () => {
  beforeEach(async () => {
    const metadataServiceSpy = jasmine.createSpyObj('MetadataService', ['initialize', 'getProjectName']);
    metadataServiceSpy.initialize.and.returnValue(of({}));
    metadataServiceSpy.getProjectName.and.returnValue('TestApp');

    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [
        { provide: MetadataService, useValue: metadataServiceSpy },
        { provide: NavigationService, useValue: {} },
        { provide: ConfigService, useValue: { config: { server_url: 'http://test' } } },
        { provide: RestService, useValue: {} }
      ]
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it(`should have the default title initially`, () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app.title).toEqual('ui');
  });

  it('should update title after initialization', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    app.ngOnInit();
    expect(app.title).toEqual('TestApp');
  });

  it('should render navigation', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.nav-link')?.textContent).toContain('TestApp Management');
  });
});
