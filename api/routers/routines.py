from pydantic import BaseModel
from typing import List, Optional
from fastapi import APIRouter
from sqlalchemy.orm import joinedload
from api.models import Workout, Routine
from api.deps import db_dependency, user_dependency

router = APIRouter(
    prefix='/routines',
    tags=['routines']
)

class RoutineBase(BaseModel):
    name: str
    description: Optional[str] = None
    
class RoutineCreate(RoutineBase):
    workouts: List[int] = []

class RoutineResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: str
    workouts: List[int]
  

class RoutinesPageResponse(BaseModel):
    routines: List[RoutineResponse]
    previousCursor: Optional[str]
    
@router.get("/",response_model=RoutinesPageResponse)
def get_routines(db: db_dependency, user: user_dependency,cursor: Optional[str] = None,limit: int = 10):
    query = (
        db.query(Routine)
        .options(joinedload(Routine.workouts))
        .filter(Routine.user_id == user.get("id"))
    )

    if cursor:
        query = query.filter(Routine.id < int(cursor))

    routines = (
        query.order_by(Routine.id.desc()) 
        .limit(limit)
        .all()
    )

    previous_cursor = None
    if routines and len(routines) == limit:
        previous_cursor = str(routines[-1].id)

    routines_response = [
        RoutineResponse(
            id=routine.id,
            user_id=routine.user_id,
            name=routine.name,
            description=routine.description,
            workouts=[workout.id for workout in routine.workouts]
        )
        for routine in routines
    ]

    return {
        "routines": routines_response,
        "previousCursor": previous_cursor
    }

@router.post("/")
def create_routine(db: db_dependency, user: user_dependency, routine: RoutineCreate):
    db_routine = Routine(name=routine.name, description=routine.description, user_id=user.get('id'))
    for workout_id in routine.workouts:
        workout = db.query(Workout).filter(Workout.id == workout_id).first()
        if workout:
            db_routine.workouts.append(workout)
    db.add(db_routine)
    db.commit()
    db.refresh(db_routine)
    db_routines = db.query(Routine).options(joinedload(Routine.workouts)).filter(Routine.id == db_routine.id).first()
    return db_routines

@router.delete('/')
def delete_routine(db: db_dependency, user: user_dependency, routine_id: int):
    db_routine = db.query(Routine).filter(Routine.id == routine_id).first()
    if db_routine:
        db.delete(db_routine)
        db.commit()
    return db_routine