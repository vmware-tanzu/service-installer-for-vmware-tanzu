import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';

import { Messenger } from './Messenger';

describe('Messenger', () => {
    let service: Messenger;

    beforeEach(() => TestBed.configureTestingModule({
        imports: [
            HttpClientTestingModule
        ],
        providers: [
            Messenger
        ]
    }));

    beforeEach(() => {
        service = TestBed.get(Messenger);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });
});
