// Death "poof": the body disappears at once and a burst of white smoke, sized to the body, puffs up and drifts away.
// ADeathSmoke::Poof(Actor) is called by every enemy, boss and the player on death. The smoke is camera-facing cards
// (one instanced mesh, engine plane) with M_DeathSmoke: an 8x8 flipbook of a Mantaflow smoke burst rendered in Blender
// (Export/Blender/scripts/props/gen_death_smoke_sim.py, Tools/import_death_smoke.py). Per-instance custom data:
// 0 = flipbook frame (0..63, blended), 1 = opacity.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DeathSmoke.generated.h"

class UInstancedStaticMeshComponent;

UCLASS()
class ADeathSmoke : public AActor
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UInstancedStaticMeshComponent* Puffs;

public:

	ADeathSmoke();

	/** Hides the actor right away (physics + collision of its meshes off) and spawns smoke that covers its visible body.
	 *  The caller brings the actor back later with SetActorHiddenInGame(false) (enemy reset / player respawn). */
	static ADeathSmoke* Poof(AActor* Dead);

	/** The same smoke over the actor's visible body, but the actor stays as it is (e.g. the player's model swap) */
	static ADeathSmoke* Burst(AActor* Target);

	virtual void Tick(float DeltaSeconds) override;

protected:

	/** Seconds a puff lives (each one varies a little) */
	UPROPERTY(EditAnywhere, Category="Death Smoke", meta = (ClampMin = 0.2, Units = "s"))
	float Duration = 1.7f;

	/** Puffs for a mannequin-sized body; scales with the body volume */
	UPROPERTY(EditAnywhere, Category="Death Smoke", meta = (ClampMin = 1))
	int32 BasePuffs = 6;

	UPROPERTY(EditAnywhere, Category="Death Smoke", meta = (ClampMin = 1))
	int32 MaxPuffs = 30;

	/** Puff size relative to the body's half width / height */
	UPROPERTY(EditAnywhere, Category="Death Smoke", meta = (ClampMin = 0.1))
	float PuffSizeScale = 1.f;

private:

	struct FPuff
	{
		FVector Position;
		FVector Velocity;
		float StartSize;
		float EndSize;
		float Life;
		float Delay;
		float Roll;
		float RollSpeed;
	};
	TArray<FPuff> PuffData;
	float Age = 0.f;

	void Start(const FBox& Body);
};
