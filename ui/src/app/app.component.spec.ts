import { TestBed } from '@angular/core/testing';
import { AppComponent } from './app.component';
import { MetadataService } from './services/metadata.service';
import { NavigationService } from './services/navigation.service';
import { ConfigService } from './services/config.service';
import { RestService } from './services/rest.service';
import { NotificationComponent } from './components/notification.component';
import { of } from 'rxjs';

describe('AppComponent', () => {
  let metadataServiceSpy: jasmine.SpyObj<MetadataService>;

  beforeEach(async () => {
    metadataServiceSpy = jasmine.createSpyObj('MetadataService', ['initialize', 'getProjectName']);
    metadataServiceSpy.initialize.and.returnValue(of({ projectName: 'ui', entities: [] }));
    metadataServiceSpy.getProjectName.and.returnValue('ui');

    await TestBed.configureTestingModule({
      imports: [AppComponent, NotificationComponent],
      providers: [
        { provide: MetadataService, useValue: metadataServiceSpy },
        { provide: NavigationService, useValue: {} },
        { provide: ConfigService, useValue: { config: { server_url: '' } } },
        { provide: RestService, useValue: {} }
      ]
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it(`should have the 'ui' title initially`, () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app.title).toEqual('ui');
  });

  it('should update title after initialization', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    app.ngOnInit();
    expect(app.title).toEqual('ui');
  });

  it('should render title', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.nav-link')?.textContent).toContain('ui Management');
  });
});
