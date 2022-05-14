// Angular imports
import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
    providedIn: 'root'
})
export class AppDataService {

    private providerType = new BehaviorSubject<string|null>(null);
    private infraType = new BehaviorSubject<string|null>(null);
    private hasPacificCluster = new BehaviorSubject<boolean>(false);
    private tkrVersion = new BehaviorSubject<string|null>(null);
    private featureFlags = new BehaviorSubject<Map<String, String>|null>(null);

    constructor() {
        this.providerType.asObservable().subscribe((data) => {
            if (data) {
                console.log("ARCAS UI launched with provider type ---------> " + data);
            }
        });
        this.infraType.asObservable().subscribe((data) => {
            if (data) {
                console.log("ARCAS UI launched with infra type ---------> " + data);
            }
        });
    }

    setProviderType(provider: string) {
        this.providerType.next(provider);
    }

    getProviderType() {
        return this.providerType;
    }

    setInfraType(infra: string) {
        this.infraType.next(infra);
    }

    getInfraType() {
        return this.infraType;
    }

    setIsProjPacific(flag: boolean) {
        this.hasPacificCluster.next(flag);
    }

    getIsProjPacific() {
        return this.hasPacificCluster;
    }

    setTkrVersion(version: string) {
        this.tkrVersion.next(version);
    }

    getTkrVersion() {
        return this.tkrVersion;
    }

    setFeatureFlags(flags: Map<String, String>) {
        this.featureFlags.next(flags);
    }

    getFeatureFlags() {
        return this.featureFlags;
    }
}
